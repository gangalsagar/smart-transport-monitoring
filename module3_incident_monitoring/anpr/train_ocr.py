#!/usr/bin/env python3
"""
Module 3 Indian License Plate CRNN OCR Architecture & Training Pipeline
========================================================================
Lightweight CRNN (CNN + BiLSTM + CTC Loss) designed for CPU training and Edge AI inference.

Vocabulary: 0-9, A-Z (36 characters + blank index 0)
Image Pipeline: Grayscale, aspect-ratio-preserving resize with zero-padding (48 x 160)
Augmentation: Training-only mild affine rotation, brightness/contrast jitter, and Gaussian blur.
Metrics: CTC Loss, Exact Match Accuracy, Character Accuracy, Character Error Rate (CER).
"""

import os
import sys
import time
import json
import random
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# =====================================================================
# Constants & Vocabulary
# =====================================================================
CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BLANK_IDX = 0

CHAR_TO_IDX = {c: i + 1 for i, c in enumerate(CHARS)}
IDX_TO_CHAR = {i + 1: c for i, c in enumerate(CHARS)}
NUM_CLASSES = len(CHARS) + 1  # 36 + 1 blank = 37

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

# =====================================================================
# Levenshtein Distance for CER Calculation
# =====================================================================
def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def calculate_metrics(predictions, ground_truths):
    total_samples = len(predictions)
    if total_samples == 0:
        return 0.0, 0.0, 0.0

    exact_matches = 0
    total_dist = 0
    total_ref_chars = 0
    correct_chars = 0

    for pred, gt in zip(predictions, ground_truths):
        pred_clean = pred.strip().upper()
        gt_clean = gt.strip().upper()

        if pred_clean == gt_clean:
            exact_matches += 1

        dist = levenshtein_distance(pred_clean, gt_clean)
        total_dist += dist
        ref_len = len(gt_clean)
        total_ref_chars += ref_len

        # Character match count (max reference length minus distance)
        matched = max(0, ref_len - dist)
        correct_chars += matched

    exact_acc = exact_matches / total_samples
    cer = total_dist / max(1, total_ref_chars)
    char_acc = correct_chars / max(1, total_ref_chars)

    return exact_acc, char_acc, cer

# =====================================================================
# Data Preprocessing & Augmentation
# =====================================================================
class PlateAugmentation:
    def __init__(self, apply=True):
        self.apply = apply

    def __call__(self, img: Image.Image) -> Image.Image:
        if not self.apply:
            return img

        # 1. Mild Random Rotation (-5 to +5 degrees)
        if random.random() < 0.5:
            angle = random.uniform(-5.0, 5.0)
            img = img.rotate(angle, resample=Image.BILINEAR, expand=False, fillcolor=128)

        # 2. Mild Brightness Jitter (0.8 to 1.2)
        if random.random() < 0.4:
            factor = random.uniform(0.8, 1.2)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(factor)

        # 3. Mild Contrast Jitter (0.8 to 1.2)
        if random.random() < 0.4:
            factor = random.uniform(0.8, 1.2)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(factor)

        # 4. Mild Gaussian Blur
        if random.random() < 0.2:
            img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.8)))

        return img

def resize_and_pad(img: Image.Image, target_h=48, target_w=160) -> np.ndarray:
    """
    Resize image preserving aspect ratio and pad with neutral gray (128)
    to prevent unnatural horizontal/vertical stretching.
    """
    orig_w, orig_h = img.size
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = max(1, int(orig_w * scale))
    new_h = max(1, int(orig_h * scale))

    resized_img = img.resize((new_w, new_h), Image.BILINEAR)
    pad_img = Image.new("L", (target_w, target_h), color=128)
    pad_x = (target_w - new_w) // 2
    pad_y = (target_h - new_h) // 2
    pad_img.paste(resized_img, (pad_x, pad_y))

    arr = np.array(pad_img, dtype=np.float32) / 255.0
    arr = (arr - 0.5) / 0.5  # Standardize around 0 [-1.0, 1.0]
    return arr

class IndianPlateOCRDataset(Dataset):
    def __init__(self, csv_file, images_dir, img_h=48, img_w=160, is_training=False):
        self.df = pd.read_csv(csv_file)
        self.images_dir = Path(images_dir)
        self.img_h = img_h
        self.img_w = img_w
        self.augmentor = PlateAugmentation(apply=is_training)

        # Clean labels
        self.samples = []
        for _, row in self.df.iterrows():
            img_name = str(row["image"]).strip()
            text = str(row["text"]).strip().upper()
            text_clean = "".join([c for c in text if c in CHAR_TO_IDX])
            img_path = self.images_dir / img_name
            if len(text_clean) > 0 and img_path.exists():
                self.samples.append((img_path, text_clean))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, text = self.samples[idx]

        try:
            img = Image.open(img_path).convert("L")
        except Exception:
            img = Image.new("L", (self.img_w, self.img_h), color=128)

        img = self.augmentor(img)
        img_arr = resize_and_pad(img, self.img_h, self.img_w)
        tensor_img = torch.tensor(img_arr, dtype=torch.float32).unsqueeze(0)  # (1, H, W)
        target = torch.tensor([CHAR_TO_IDX[c] for c in text], dtype=torch.long)

        return tensor_img, target, text

def ocr_collate_fn(batch):
    images, targets, texts = zip(*batch)
    images = torch.stack(images, 0)
    target_lengths = torch.tensor([len(t) for t in targets], dtype=torch.long)
    targets_flat = torch.cat(targets)
    return images, targets_flat, target_lengths, texts

# =====================================================================
# Lightweight CRNN Model Architecture
# =====================================================================
class CRNNOcrModel(nn.Module):
    def __init__(self, num_classes=NUM_CLASSES):
        super().__init__()
        # CNN Feature Extractor
        self.cnn = nn.Sequential(
            # Block 1: 48x160 -> 24x80
            nn.Conv2d(1, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            # Block 2: 24x80 -> 12x40
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            # Block 3: 12x40 -> 6x40
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),

            nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 1), (2, 1)),  # Height / 2, Width unchanged

            # Block 4: 6x40 -> 3x40
            nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 1), (2, 1)),  # Height / 2, Width unchanged
        )

        # Map to sequence: 512 * 3 = 1536 features per time step (T=40)
        self.rnn = nn.LSTM(
            input_size=512 * 3,
            hidden_size=256,
            num_layers=2,
            bidirectional=True,
            batch_first=True,
            dropout=0.1
        )

        # 2 * 256 = 512 -> num_classes
        self.classifier = nn.Linear(512, num_classes)

    def forward(self, x):
        # x: [B, 1, 48, 160]
        feats = self.cnn(x)  # [B, 512, 3, 40]
        b, c, h, w = feats.size()

        # Sequence along width: [B, W, C * H] -> [B, 40, 1536]
        seq = feats.permute(0, 3, 1, 2).contiguous()
        seq = seq.view(b, w, c * h)

        # BiLSTM: [B, 40, 512]
        lstm_out, _ = self.rnn(seq)

        # Classifier: [B, 40, NUM_CLASSES]
        logits = self.classifier(lstm_out)

        # PyTorch CTC Loss expects: [Time_steps, Batch_size, Num_classes]
        logits_ctc = logits.permute(1, 0, 2)
        return logits_ctc

# =====================================================================
# Greedy CTC Decoder
# =====================================================================
def greedy_ctc_decode(logits_ctc: torch.Tensor) -> list:
    # logits_ctc: [T, B, C]
    probs = logits_ctc.softmax(2)
    preds = torch.argmax(probs, dim=2)  # [T, B]
    preds = preds.permute(1, 0).detach().cpu().numpy()  # [B, T]

    decoded_strings = []
    for seq in preds:
        chars = []
        prev = None
        for idx in seq:
            if idx != BLANK_IDX and idx != prev:
                if idx in IDX_TO_CHAR:
                    chars.append(IDX_TO_CHAR[idx])
            prev = idx
        decoded_strings.append("".join(chars))

    return decoded_strings

# =====================================================================
# Epoch Runner
# =====================================================================
def run_epoch(model, loader, criterion, optimizer, device, is_train=True):
    if is_train:
        model.train()
    else:
        model.eval()

    total_loss = 0.0
    all_preds = []
    all_targets = []
    total_samples = 0

    for images, targets_flat, target_lengths, text_labels in loader:
        b_size = images.size(0)
        images = images.to(device)
        targets_flat = targets_flat.to(device)
        target_lengths = target_lengths.to(device)

        if is_train:
            optimizer.zero_grad()

        with torch.set_grad_enabled(is_train):
            logits_ctc = model(images)  # [T, B, C]
            time_steps = logits_ctc.size(0)
            input_lengths = torch.full((b_size,), time_steps, dtype=torch.long, device=device)

            loss = criterion(logits_ctc.log_softmax(2), targets_flat, input_lengths, target_lengths)

            if is_train:
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

        total_loss += loss.item() * b_size
        total_samples += b_size

        # Decode predictions
        decoded = greedy_ctc_decode(logits_ctc)
        all_preds.extend(decoded)
        all_targets.extend(text_labels)

    avg_loss = total_loss / max(1, total_samples)
    exact_acc, char_acc, cer = calculate_metrics(all_preds, all_targets)

    return avg_loss, exact_acc, char_acc, cer

# =====================================================================
# Main Training Entrypoint
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="Train CRNN OCR for Indian License Plates")
    parser.add_argument("--data-dir", type=str, default="module3_incident_anpr/indian_license_plate_ocr")
    parser.add_argument("--checkpoint-dir", type=str, default="module3_incident_anpr/ocr_checkpoints")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--img-height", type=int, default=48)
    parser.add_argument("--img-width", type=int, default=160)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    data_dir = Path(args.data_dir)
    images_dir = data_dir / "images"
    train_csv = data_dir / "train.csv"
    val_csv = data_dir / "val.csv"

    output_dir = Path(args.checkpoint_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("INDIAN LICENSE PLATE OCR TRAINING (CRNN + CTC)")
    print("=" * 75)
    print(f"Device:             {device}")
    print(f"Data Directory:     {data_dir}")
    print(f"Checkpoints Dir:    {output_dir}")
    print(f"Epochs:             {args.epochs}")
    print(f"Batch Size:         {args.batch_size}")
    print(f"Learning Rate:      {args.lr}")
    print(f"Input Resolution:   {args.img_height}x{args.img_width} (Grayscale Pad)")
    print(f"Character Classes:  {NUM_CLASSES} (Blank=0, Chars={len(CHARS)})")
    print("=" * 75)

    # Validate dataset
    if not train_csv.exists() or not val_csv.exists() or not images_dir.exists():
        print(f"[-] ERROR: Required dataset files missing in {data_dir}")
        sys.exit(1)

    train_dataset = IndianPlateOCRDataset(train_csv, images_dir, args.img_height, args.img_width, is_training=True)
    val_dataset = IndianPlateOCRDataset(val_csv, images_dir, args.img_height, args.img_width, is_training=False)

    print(f"[+] Loaded {len(train_dataset)} training samples, {len(val_dataset)} validation samples.")

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        collate_fn=ocr_collate_fn
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=ocr_collate_fn
    )

    model = CRNNOcrModel(num_classes=NUM_CLASSES).to(device)
    criterion = nn.CTCLoss(blank=BLANK_IDX, zero_infinity=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

    best_cer = float("inf")
    best_exact = 0.0
    history = []

    print("\nStarting Training Epochs...")
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss, train_exact, train_char, train_cer = run_epoch(
            model, train_loader, criterion, optimizer, device, is_train=True
        )
        val_loss, val_exact, val_char, val_cer = run_epoch(
            model, val_loader, criterion, optimizer, device, is_train=False
        )
        epoch_time = time.time() - t0

        scheduler.step(val_cer)

        print(
            f"Epoch {epoch:02d}/{args.epochs:02d} [{epoch_time:.1f}s] | "
            f"Train Loss: {train_loss:.4f} Exact: {train_exact:.2%} CER: {train_cer:.3f} | "
            f"Val Loss: {val_loss:.4f} Exact: {val_exact:.2%} CharAcc: {val_char:.2%} CER: {val_cer:.3f}"
        )

        epoch_record = {
            "epoch": epoch,
            "epoch_time_sec": round(epoch_time, 2),
            "train_loss": round(train_loss, 4),
            "train_exact_accuracy": round(train_exact, 4),
            "train_char_accuracy": round(train_char, 4),
            "train_cer": round(train_cer, 4),
            "val_loss": round(val_loss, 4),
            "val_exact_accuracy": round(val_exact, 4),
            "val_char_accuracy": round(val_char, 4),
            "val_cer": round(val_cer, 4)
        }
        history.append(epoch_record)

        # Checkpoint structure
        checkpoint_payload = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "characters": CHARS,
            "num_classes": NUM_CLASSES,
            "img_height": args.img_height,
            "img_width": args.img_width,
            "val_metrics": {
                "exact_accuracy": val_exact,
                "char_accuracy": val_char,
                "cer": val_cer,
                "loss": val_loss
            }
        }

        # Save latest
        torch.save(checkpoint_payload, output_dir / "latest_ocr_model.pt")

        # Save best by lowest CER (or highest exact accuracy on tie)
        if val_cer < best_cer or (val_cer == best_cer and val_exact > best_exact):
            best_cer = val_cer
            best_exact = val_exact
            torch.save(checkpoint_payload, output_dir / "best_ocr_model.pt")
            print(f"  [+] Saved new best checkpoint -> CER: {val_cer:.3f}, Exact Acc: {val_exact:.2%}")

    # Write history JSON
    with open(output_dir / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    print("\n" + "=" * 75)
    print("OCR TRAINING COMPLETE")
    print(f"Best Validation CER:            {best_cer:.4f}")
    print(f"Best Validation Exact Match:    {best_exact:.2%}")
    print(f"Best Checkpoint:                {output_dir / 'best_ocr_model.pt'}")
    print(f"Latest Checkpoint:              {output_dir / 'latest_ocr_model.pt'}")
    print(f"Training History Log:           {output_dir / 'training_history.json'}")
    print("=" * 75)

if __name__ == "__main__":
    main()
