#!/usr/bin/env python3
"""
Create Q1000 Indian License Plate OCR Dataset Experiment
=========================================================
Filters training and validation sets to exclude low-resolution crops (< 1000 pixels = width * height).
Keeps the test set completely intact (all 170 samples) to ensure strict benchmark comparability.

Original baseline dataset remains 100% untouched.
"""

import sys
import shutil
from pathlib import Path
import pandas as pd
from PIL import Image

def create_q1000_dataset(
    source_dir="module3_incident_anpr/indian_license_plate_ocr",
    output_dir="module3_incident_anpr/indian_license_plate_ocr_q1000",
    threshold=1000
):
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    images_out_path = output_path / "images"

    print("=" * 70)
    print("CREATING Q1000 OCR DATASET EXPERIMENT (FILTER: >= 1000 PIXELS)")
    print(f"Source Dataset: {source_path}")
    print(f"Output Dataset: {output_path}")
    print(f"Pixel Threshold (W x H): >= {threshold} px")
    print("=" * 70)

    if not source_path.exists():
        print(f"[-] ERROR: Source dataset '{source_path}' does not exist.")
        sys.exit(1)

    images_out_path.mkdir(parents=True, exist_ok=True)
    source_images_path = source_path / "images"

    stats = {}

    for split in ["train", "val", "test"]:
        csv_file = source_path / f"{split}.csv"
        if not csv_file.exists():
            print(f"[-] ERROR: Missing split file: {csv_file}")
            sys.exit(1)

        df = pd.read_csv(csv_file)
        orig_count = len(df)

        if split == "test":
            # Test set must remain 100% untouched
            df.to_csv(output_path / "test.csv", index=False)
            stats["test"] = {"original": orig_count, "filtered": orig_count, "rejected": 0}
            print(f"[+] TEST  : Kept ALL {orig_count} samples (untouched benchmark)")
            continue

        keep_rows = []
        rejected_count = 0

        for _, row in df.iterrows():
            img_name = str(row["image"]).strip()
            img_file = source_images_path / img_name

            if not img_file.exists():
                print(f"[-] Warning: Image not found: {img_file}")
                rejected_count += 1
                continue

            try:
                with Image.open(img_file) as im:
                    w, h = im.size
                    pixels = w * h

                if pixels >= threshold:
                    keep_rows.append(row)
                else:
                    rejected_count += 1
            except Exception as e:
                print(f"[-] Error reading {img_file}: {e}")
                rejected_count += 1

        filtered_df = pd.DataFrame(keep_rows)
        out_csv = output_path / f"{split}.csv"
        filtered_df.to_csv(out_csv, index=False)
        stats[split] = {"original": orig_count, "filtered": len(filtered_df), "rejected": rejected_count}

        print(
            f"[+] {split.upper():5} : {orig_count} -> {len(filtered_df)} samples "
            f"(filtered out {rejected_count} samples < {threshold} px)"
        )

    # Ensure all referenced images are present in the output images directory
    all_referenced_images = set()
    for split in ["train", "val", "test"]:
        split_df = pd.read_csv(output_path / f"{split}.csv")
        all_referenced_images.update(split_df["image"].tolist())

    copied_count = 0
    for img_name in all_referenced_images:
        src_img = source_images_path / img_name
        dst_img = images_out_path / img_name
        if not dst_img.exists() and src_img.exists():
            shutil.copy2(src_img, dst_img)
            copied_count += 1

    print(f"\n[+] Total unique images verified in output directory: {len(all_referenced_images)}")
    if copied_count > 0:
        print(f"[+] Copied {copied_count} new images to {images_out_path}")

    # Generate complete labels.csv for Q1000
    q1000_train = pd.read_csv(output_path / "train.csv")
    q1000_val = pd.read_csv(output_path / "val.csv")
    q1000_test = pd.read_csv(output_path / "test.csv")
    q1000_all = pd.concat([q1000_train, q1000_val, q1000_test], ignore_index=True)
    q1000_all.to_csv(output_path / "labels.csv", index=False)

    print(f"[+] Generated combined labels.csv with {len(q1000_all)} total rows.")
    print("=" * 70)
    print("Q1000 DATASET CREATION COMPLETE")
    print(f"Train samples: {len(q1000_train)} (from {stats['train']['original']})")
    print(f"Val samples:   {len(q1000_val)} (from {stats['val']['original']})")
    print(f"Test samples:  {len(q1000_test)} (from {stats['test']['original']} - Unchanged)")
    print("=" * 70)

if __name__ == "__main__":
    create_q1000_dataset()
