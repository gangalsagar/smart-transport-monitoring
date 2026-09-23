#!/usr/bin/env python3
"""
Module 3 OCR Independent Test Set Evaluator with Configurable CTC Decoders
==========================================================================
Evaluates OCR checkpoints against test.csv with:
- Greedy CTC Decoder (Baseline)
- CTC Prefix Beam Search Decoder (Configurable beam width)

Calculates:
- Exact Plate Match Accuracy
- Character Accuracy
- Character Error Rate (CER)
- Average & Median CPU inference latency per plate (milliseconds)
- Exports detailed predictions to output JSON
"""

import os
import sys
import time
import math
import json
import argparse
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# Import shared architecture and utilities from train_ocr
from train_ocr import (
    CHARS, BLANK_IDX, CHAR_TO_IDX, IDX_TO_CHAR, NUM_CLASSES,
    CRNNOcrModel, resize_and_pad, greedy_ctc_decode, calculate_metrics, ocr_collate_fn
)

def ctc_prefix_beam_search(logits_ctc: torch.Tensor, beam_width: int = 10, blank_idx: int = BLANK_IDX) -> list:
    """
    Standard CTC Prefix Beam Search Decoder.
    logits_ctc: Tensor of shape [Time_steps, Batch_size, Num_classes]
    Returns list of decoded strings of length Batch_size.
    """
    # Softmax over classes -> probabilities [T, B, C]
    probs = logits_ctc.softmax(dim=2).detach().cpu().numpy()
    T, B, C = probs.shape

    decoded_strings = []

    for b in range(B):
        # Beam states: prefix (tuple of char_indices) -> (p_blank, p_non_blank) in log space or probability space
        # Using probability space for fast CPU execution
        # Initialize with empty prefix
        beam = {(): (1.0, 0.0)}  # prefix: (p_b, p_nb)

        for t in range(T):
            t_probs = probs[t, b]  # [C]
            next_beam = defaultdict(lambda: (0.0, 0.0))

            # Prune step probabilities to top-(beam_width * 2) to accelerate execution
            top_indices = np.argsort(t_probs)[::-1][:max(beam_width * 2, 10)]

            for prefix, (p_b, p_nb) in beam.items():
                p_total = p_b + p_nb
                if p_total <= 0.0:
                    continue

                for c in top_indices:
                    p_c = float(t_probs[c])
                    if p_c <= 0.0:
                        continue

                    if c == blank_idx:
                        # Blank token extends current prefix in blank state
                        curr_b, curr_nb = next_beam[prefix]
                        next_beam[prefix] = (curr_b + (p_total * p_c), curr_nb)
                    else:
                        end_char = prefix[-1] if len(prefix) > 0 else None
                        
                        if c == end_char:
                            # If character is same as last character:
                            # 1. Extending from blank state creates repeated character (e.g. '0' -> '00')
                            new_prefix = prefix + (c,)
                            curr_b, curr_nb = next_beam[new_prefix]
                            next_beam[new_prefix] = (curr_b, curr_nb + (p_b * p_c))

                            # 2. Extending from non-blank state collapses into single character (e.g. '0' -> '0')
                            curr_b, curr_nb = next_beam[prefix]
                            next_beam[prefix] = (curr_b, curr_nb + (p_nb * p_c))
                        else:
                            # Different character extends prefix
                            new_prefix = prefix + (c,)
                            curr_b, curr_nb = next_beam[new_prefix]
                            next_beam[new_prefix] = (curr_b, curr_nb + (p_total * p_c))

            # Prune to top beam_width prefixes by total probability
            sorted_prefixes = sorted(
                next_beam.keys(),
                key=lambda pref: next_beam[pref][0] + next_beam[pref][1],
                reverse=True
            )[:beam_width]

            beam = {pref: next_beam[pref] for pref in sorted_prefixes}

        # Select best prefix from final beam
        best_prefix = max(beam.keys(), key=lambda pref: beam[pref][0] + beam[pref][1]) if beam else ()
        decoded_text = "".join([IDX_TO_CHAR[idx] for idx in best_prefix if idx in IDX_TO_CHAR])
        decoded_strings.append(decoded_text)

    return decoded_strings

class TestPlateDataset(Dataset):
    def __init__(self, csv_file, images_dir, img_h=48, img_w=160):
        self.df = pd.read_csv(csv_file)
        self.images_dir = Path(images_dir)
        self.img_h = img_h
        self.img_w = img_w
        self.samples = []
        for _, row in self.df.iterrows():
            img_name = str(row["image"]).strip()
            text = str(row["text"]).strip().upper()
            text_clean = "".join([c for c in text if c in CHAR_TO_IDX])
            img_path = self.images_dir / img_name
            if len(text_clean) > 0 and img_path.exists():
                self.samples.append((img_path, img_name, text_clean))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, img_name, text = self.samples[idx]
        try:
            img = Image.open(img_path).convert("L")
        except Exception:
            img = Image.new("L", (self.img_w, self.img_h), color=128)

        img_arr = resize_and_pad(img, self.img_h, self.img_w)
        tensor_img = torch.tensor(img_arr, dtype=torch.float32).unsqueeze(0)
        target = torch.tensor([CHAR_TO_IDX[c] for c in text], dtype=torch.long)
        return tensor_img, target, text, img_name

def test_collate_fn(batch):
    images, targets, texts, img_names = zip(*batch)
    images = torch.stack(images, 0)
    target_lengths = torch.tensor([len(t) for t in targets], dtype=torch.long)
    targets_flat = torch.cat(targets)
    return images, targets_flat, target_lengths, texts, img_names

def evaluate_test_set(checkpoint_path: str, data_dir: str, output_results_path: str, decoder_type: str = "greedy", beam_width: int = 10):
    print("=" * 75)
    print("INDEPENDENT OCR TEST SET EVALUATION (MODULE 3 ANPR)")
    print(f"Checkpoint:       {checkpoint_path}")
    print(f"Dataset:          {data_dir}")
    print(f"Decoding Strategy: {decoder_type.upper()}" + (f" (Beam Width = {beam_width})" if decoder_type == "beam" else ""))
    print("=" * 75)

    device = torch.device("cpu")
    checkpoint_file = Path(checkpoint_path)
    if not checkpoint_file.exists():
        print(f"[-] ERROR: Checkpoint file not found at {checkpoint_path}")
        return False

    checkpoint = torch.load(checkpoint_path, map_location=device)
    img_h = checkpoint.get("img_height", 48)
    img_w = checkpoint.get("img_width", 160)
    num_classes = checkpoint.get("num_classes", NUM_CLASSES)

    model = CRNNOcrModel(num_classes=num_classes).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    test_csv = Path(data_dir) / "test.csv"
    images_dir = Path(data_dir) / "images"

    if not test_csv.exists() or not images_dir.exists():
        print(f"[-] ERROR: Test set files missing in {data_dir}")
        return False

    test_dataset = TestPlateDataset(test_csv, images_dir, img_h=img_h, img_w=img_w)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False, num_workers=0, collate_fn=test_collate_fn)

    print(f"[+] Loaded {len(test_dataset)} test samples from {test_csv}")

    all_preds = []
    all_targets = []
    all_names = []
    inference_times = []

    print(f"\nRunning {decoder_type.upper()} Inference on Test Set...")
    with torch.no_grad():
        for images, targets_flat, target_lengths, texts, img_names in test_loader:
            images = images.to(device)

            t0 = time.perf_counter()
            logits_ctc = model(images)

            if decoder_type == "beam":
                decoded = ctc_prefix_beam_search(logits_ctc, beam_width=beam_width, blank_idx=BLANK_IDX)
            else:
                decoded = greedy_ctc_decode(logits_ctc)

            t1 = time.perf_counter()
            inference_times.append((t1 - t0) * 1000.0)  # ms

            all_preds.extend(decoded)
            all_targets.extend(texts)
            all_names.extend(img_names)

    exact_acc, char_acc, cer = calculate_metrics(all_preds, all_targets)
    avg_latency_ms = float(np.mean(inference_times))
    median_latency_ms = float(np.median(inference_times))

    # Print 20 sample comparisons
    print("\n" + "=" * 75)
    print(f"SAMPLE TEST PREDICTIONS ({decoder_type.upper()} DECODER - 20 EXAMPLES)")
    print("=" * 75)
    print(f"{'Image File':<20} | {'Ground Truth':<15} | {'Prediction':<15} | {'Status'}")
    print("-" * 75)
    for i in range(min(20, len(all_preds))):
        img_f = all_names[i]
        gt = all_targets[i]
        pr = all_preds[i]
        status = "MATCH [OK]" if gt == pr else "MISMATCH"
        print(f"{img_f:<20} | {gt:<15} | {pr:<15} | {status}")

    # Build results JSON
    results = {
        "checkpoint": str(checkpoint_path),
        "decoder": decoder_type,
        "beam_width": beam_width if decoder_type == "beam" else 1,
        "test_samples_evaluated": len(all_preds),
        "metrics": {
            "exact_plate_accuracy": round(exact_acc, 4),
            "character_accuracy": round(char_acc, 4),
            "character_error_rate_cer": round(cer, 4),
            "average_cpu_latency_ms": round(avg_latency_ms, 2),
            "median_cpu_latency_ms": round(median_latency_ms, 2)
        },
        "predictions": [
            {
                "image": all_names[i],
                "ground_truth": all_targets[i],
                "prediction": all_preds[i],
                "exact_match": (all_targets[i] == all_preds[i]),
                "latency_ms": round(inference_times[i], 2)
            }
            for i in range(len(all_preds))
        ]
    }

    out_file = Path(output_results_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 75)
    print(f"TEST SET EVALUATION SUMMARY ({decoder_type.upper()} DECODER)")
    print("=" * 75)
    print(f"Total Test Samples:             {len(all_preds)}")
    print(f"Exact Plate Accuracy:           {exact_acc:.2%}")
    print(f"Character Accuracy:             {char_acc:.2%}")
    print(f"Character Error Rate (CER):     {cer:.4f}")
    print(f"Average CPU Latency per Crop:   {avg_latency_ms:.2f} ms")
    print(f"Median CPU Latency per Crop:    {median_latency_ms:.2f} ms")
    print(f"Detailed Results Saved To:      {output_results_path}")
    print("=" * 75)

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate OCR Model on Independent Test Set with Configurable Decoder")
    parser.add_argument("--checkpoint", type=str, default="module3_incident_anpr/ocr_checkpoints/best_ocr_model.pt")
    parser.add_argument("--data-dir", type=str, default="module3_incident_anpr/indian_license_plate_ocr")
    parser.add_argument("--output", type=str, default="module3_incident_anpr/ocr_test_results.json")
    parser.add_argument("--decoder", type=str, choices=["greedy", "beam"], default="greedy")
    parser.add_argument("--beam-width", type=int, default=10)
    args = parser.parse_args()

    evaluate_test_set(
        checkpoint_path=args.checkpoint,
        data_dir=args.data_dir,
        output_results_path=args.output,
        decoder_type=args.decoder,
        beam_width=args.beam_width
    )
