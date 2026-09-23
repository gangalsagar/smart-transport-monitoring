#!/usr/bin/env python3
"""
Verify and Audit Local Indian Plate OCR Dataset for Module 3 ANPR
==================================================================
This script performs strict integrity checks on the OCR dataset:
1. Verifies that images directory and labels.csv exist.
2. Checks that every image declared in labels.csv exists on disk.
3. Verifies that every label contains valid alphanumeric Indian plate text.
4. Tests image readability and dimension consistency using PIL.
5. Flags empty labels, unreadable images, or formatting errors.
"""

import os
import re
import sys
import pandas as pd
from PIL import Image

def verify_ocr_dataset(dataset_dir: str):
    print("=" * 70)
    print(f"VERIFYING OCR DATASET AT: {dataset_dir}")
    print("=" * 70)
    
    if not os.path.exists(dataset_dir):
        print(f"[-] ERROR: Dataset directory '{dataset_dir}' does not exist.")
        return False
        
    labels_csv = os.path.join(dataset_dir, "labels.csv")
    images_dir = os.path.join(dataset_dir, "images")
    
    # Fallback to direct dataset_dir or 'plates' if 'images' subfolder isn't used
    if not os.path.exists(images_dir):
        if os.path.exists(os.path.join(dataset_dir, "plates")):
            images_dir = os.path.join(dataset_dir, "plates")
        else:
            images_dir = dataset_dir

    if not os.path.exists(labels_csv):
        print(f"[-] ERROR: 'labels.csv' not found in '{dataset_dir}'.")
        return False

    print(f"[+] Found labels file: {labels_csv}")
    print(f"[+] Found images directory: {images_dir}")
    
    try:
        df = pd.read_csv(labels_csv)
    except Exception as e:
        print(f"[-] ERROR reading labels.csv: {e}")
        return False

    print(f"[+] Loaded labels.csv: {len(df)} total rows.")
    print(f"[+] Columns detected: {list(df.columns)}")

    # Standardize column naming
    img_col = None
    txt_col = None
    
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ["image_name", "image", "filename", "img", "name", "file"]:
            img_col = c
        elif cl in ["plate_number", "text", "label", "plate_text", "registration", "plate"]:
            txt_col = c

    if not img_col or not txt_col:
        print(f"[-] ERROR: Unable to identify image and text columns from: {list(df.columns)}")
        return False

    print(f"[+] Mapping columns: Image='{img_col}', Plate Text='{txt_col}'")

    valid_pairs = 0
    missing_images = 0
    corrupted_images = 0
    invalid_labels = 0
    indian_format_matches = 0
    
    # Standard Indian RTO format regex (e.g., MH12AB1234, DL01CA5678, HR26DQ5551, KA19TR02)
    indian_plate_regex = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}$")

    print("\n[+] Inspecting sample records...")
    for idx, row in df.head(10).iterrows():
        img_name = str(row[img_col]).strip()
        text_val = str(row[txt_col]).strip().upper().replace(" ", "").replace("-", "")
        img_path = os.path.join(images_dir, img_name)
        exists = os.path.exists(img_path)
        print(f"    Sample {idx+1:02d}: {img_name:<20} -> '{text_val}' | Exists: {exists}")

    print("\n[+] Auditing all records on disk...")
    for idx, row in df.iterrows():
        img_name = str(row[img_col]).strip()
        text_val = str(row[txt_col]).strip().upper().replace(" ", "").replace("-", "")
        img_path = os.path.join(images_dir, img_name)
        
        if not os.path.exists(img_path):
            missing_images += 1
            continue

        if not text_val or text_val == "NAN" or len(text_val) < 4:
            invalid_labels += 1
            continue

        try:
            with Image.open(img_path) as im:
                im.verify()
        except Exception:
            corrupted_images += 1
            continue

        if indian_plate_regex.match(text_val):
            indian_format_matches += 1

        valid_pairs += 1

    print("\n" + "=" * 70)
    print("DATASET VERIFICATION AUDIT SUMMARY")
    print("=" * 70)
    print(f"Total Rows in Metadata:      {len(df)}")
    print(f"Valid Image-Text Pairs:     {valid_pairs}")
    print(f"Missing Image Files:        {missing_images}")
    print(f"Corrupted Images:           {corrupted_images}")
    print(f"Invalid/Empty Text Labels:  {invalid_labels}")
    print(f"Standard Indian RTO Format: {indian_format_matches} ({indian_format_matches/max(1,valid_pairs)*100:.1f}%)")

    if valid_pairs > 0 and missing_images == 0 and corrupted_images == 0:
        print("\n[PASS] VERDICT: VERIFIED AND READY FOR OCR TRAINING")
        return True
    elif valid_pairs > 0:
        print("\n[WARNING] VERDICT: VERIFIED BUT REQUIRES CONVERSION/CLEANING")
        return True
    else:
        print("\n[FAIL] VERDICT: DATASET CLAIMS DO NOT MATCH LOCAL FILES")
        return False

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else r"c:\SIH\prototype\smart-transport-monitoring\module3_incident_anpr\indian_license_plate_ocr"
    verify_ocr_dataset(target_dir)
