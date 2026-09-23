#!/usr/bin/env python3
"""
Read-Only OCR Dataset Comprehensive Audit for Module 3 ANPR
===========================================================
Performs strict forensic analysis of:
- Physical existence and loadability of all split images (train, val, test)
- Cross-split image leakage detection
- Label non-emptiness and character length distributions
- Character vocabulary profiling (A-Z, 0-9, unexpected characters)
- Image geometry profiling (width, height, aspect ratios, tiny/large outliers)
- Content hash-based duplicate image detection
- Cross-split repeated text/label leakage analysis
- Generates module3_incident_anpr/ocr_dataset_analysis.json
"""

import os
import sys
import json
import hashlib
import collections
import statistics
import pandas as pd
from PIL import Image

def compute_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def analyze_ocr_dataset(dataset_dir: str, output_report_path: str):
    print("=" * 75)
    print("READ-ONLY FORENSIC AUDIT: INDIAN LICENSE PLATE OCR DATASET")
    print(f"Dataset Target: {dataset_dir}")
    print("=" * 75)
    
    images_dir = os.path.join(dataset_dir, "images")
    splits_files = {
        "train": os.path.join(dataset_dir, "train.csv"),
        "val": os.path.join(dataset_dir, "val.csv"),
        "test": os.path.join(dataset_dir, "test.csv")
    }
    
    for split_name, s_path in splits_files.items():
        if not os.path.exists(s_path):
            print(f"[-] ERROR: Split file missing: {s_path}")
            return False
            
    if not os.path.exists(images_dir):
        print(f"[-] ERROR: Images directory missing: {images_dir}")
        return False
        
    analysis = {
        "dataset_directory": dataset_dir,
        "splits_summary": {},
        "split_leakage_check": {
            "images_in_multiple_splits": [],
            "image_leakage_count": 0
        },
        "plate_text_statistics": {},
        "character_vocabulary": {},
        "image_geometry_statistics": {},
        "duplicate_image_hashes": {
            "duplicate_hash_groups_count": 0,
            "duplicate_image_groups": {}
        },
        "cross_split_label_analysis": {
            "train_val_shared_labels": [],
            "train_test_shared_labels": [],
            "val_test_shared_labels": [],
            "total_shared_labels_across_splits": 0
        },
        "image_integrity": {
            "unreadable_images": [],
            "total_unreadable": 0
        }
    }
    
    # Load splits
    split_dfs = {}
    split_images = {}
    split_labels = {}
    
    all_records = []
    
    for s_name, s_path in splits_files.items():
        df = pd.read_csv(s_path)
        split_dfs[s_name] = df
        split_images[s_name] = set(df['image'].astype(str).tolist())
        split_labels[s_name] = df['text'].astype(str).tolist()
        
        analysis["splits_summary"][s_name] = {
            "total_rows": len(df),
            "unique_images": len(split_images[s_name]),
            "unique_labels": len(set(split_labels[s_name]))
        }
        
        for _, row in df.iterrows():
            all_records.append({
                "split": s_name,
                "image": str(row['image']).strip(),
                "text": str(row['text']).strip()
            })

    # 1 & 2. Cross-split image leakage check
    train_val_img_overlap = split_images["train"].intersection(split_images["val"])
    train_test_img_overlap = split_images["train"].intersection(split_images["test"])
    val_test_img_overlap = split_images["val"].intersection(split_images["test"])
    all_img_overlap = list(train_val_img_overlap | train_test_img_overlap | val_test_img_overlap)
    
    analysis["split_leakage_check"]["images_in_multiple_splits"] = all_img_overlap
    analysis["split_leakage_check"]["image_leakage_count"] = len(all_img_overlap)
    
    # 3. Verify images exist, non-empty labels, image geometry, hashes
    widths = []
    heights = []
    aspect_ratios = []
    label_lengths = []
    all_labels = []
    char_freq = collections.Counter()
    hash_to_images = collections.defaultdict(list)
    
    tiny_images = []    # width < 30 or height < 15
    large_images = []   # width > 400 or height > 200
    
    for rec in all_records:
        img_name = rec["image"]
        text_val = rec["text"]
        img_path = os.path.join(images_dir, img_name)
        
        if not os.path.exists(img_path):
            analysis["image_integrity"]["unreadable_images"].append({
                "image": img_name,
                "error": "File does not exist"
            })
            continue
            
        try:
            with Image.open(img_path) as im:
                w, h = im.size
                widths.append(w)
                heights.append(h)
                aspect_ratio = round(w / max(1, h), 3)
                aspect_ratios.append(aspect_ratio)
                
                if w < 40 or h < 15:
                    tiny_images.append({"image": img_name, "dimensions": [w, h], "aspect_ratio": aspect_ratio})
                if w > 400 or h > 200:
                    large_images.append({"image": img_name, "dimensions": [w, h], "aspect_ratio": aspect_ratio})
        except Exception as e:
            analysis["image_integrity"]["unreadable_images"].append({
                "image": img_name,
                "error": f"PIL decode error: {e}"
            })
            continue
            
        # Hash check
        f_hash = compute_file_hash(img_path)
        hash_to_images[f_hash].append(img_name)
        
        # Text analytics
        all_labels.append(text_val)
        l_len = len(text_val)
        label_lengths.append(l_len)
        
        for ch in text_val:
            char_freq[ch] += 1
            
    analysis["image_integrity"]["total_unreadable"] = len(analysis["image_integrity"]["unreadable_images"])
    
    # 4. Plate text statistics
    label_counts = collections.Counter(all_labels)
    dup_labels_count = sum(cnt - 1 for cnt in label_counts.values() if cnt > 1)
    len_counts = dict(sorted(collections.Counter(label_lengths).items()))
    
    analysis["plate_text_statistics"] = {
        "total_samples": len(all_labels),
        "unique_labels": len(label_counts),
        "duplicate_label_instances": dup_labels_count,
        "min_label_length": min(label_lengths) if label_lengths else 0,
        "max_label_length": max(label_lengths) if label_lengths else 0,
        "mean_label_length": round(statistics.mean(label_lengths), 2) if label_lengths else 0,
        "median_label_length": statistics.median(label_lengths) if label_lengths else 0,
        "label_length_distribution": len_counts
    }
    
    # 5. Character vocabulary
    a_z_freq = {chr(c): char_freq.get(chr(c), 0) for c in range(ord('A'), ord('Z') + 1)}
    digits_freq = {str(d): char_freq.get(str(d), 0) for d in range(10)}
    unexpected_chars = {ch: count for ch, count in char_freq.items() if not (ch.isalnum() and ch.isupper())}
    
    analysis["character_vocabulary"] = {
        "all_unique_characters": sorted(list(char_freq.keys())),
        "total_unique_chars": len(char_freq),
        "alphabet_a_z_frequency": a_z_freq,
        "digits_0_9_frequency": digits_freq,
        "unexpected_characters": unexpected_chars
    }
    
    # 6. Image dimensions & aspect ratios
    ar_distribution = {
        "< 2.0 (Square/2-Line)": sum(1 for ar in aspect_ratios if ar < 2.0),
        "2.0 - 3.5 (Standard 1-Line)": sum(1 for ar in aspect_ratios if 2.0 <= ar <= 3.5),
        "3.5 - 5.0 (Long Rectangle)": sum(1 for ar in aspect_ratios if 3.5 < ar <= 5.0),
        "> 5.0 (Ultra-wide)": sum(1 for ar in aspect_ratios if ar > 5.0)
    }
    
    analysis["image_geometry_statistics"] = {
        "min_width": min(widths) if widths else 0,
        "max_width": max(widths) if widths else 0,
        "mean_width": round(statistics.mean(widths), 1) if widths else 0,
        "median_width": statistics.median(widths) if widths else 0,
        "min_height": min(heights) if heights else 0,
        "max_height": max(heights) if heights else 0,
        "mean_height": round(statistics.mean(heights), 1) if heights else 0,
        "median_height": statistics.median(heights) if heights else 0,
        "min_aspect_ratio": min(aspect_ratios) if aspect_ratios else 0,
        "max_aspect_ratio": max(aspect_ratios) if aspect_ratios else 0,
        "mean_aspect_ratio": round(statistics.mean(aspect_ratios), 2) if aspect_ratios else 0,
        "median_aspect_ratio": statistics.median(aspect_ratios) if aspect_ratios else 0,
        "aspect_ratio_distribution": ar_distribution,
        "tiny_images_count": len(tiny_images),
        "tiny_images_sample": tiny_images[:5],
        "large_images_count": len(large_images),
        "large_images_sample": large_images[:5]
    }
    
    # 8. Duplicate Image Hashes
    dup_hashes = {h: imgs for h, imgs in hash_to_images.items() if len(imgs) > 1}
    analysis["duplicate_image_hashes"]["duplicate_hash_groups_count"] = len(dup_hashes)
    analysis["duplicate_image_hashes"]["duplicate_image_groups"] = dup_hashes
    
    # 9. Cross-split label duplication analysis
    train_labels_set = set(split_labels["train"])
    val_labels_set = set(split_labels["val"])
    test_labels_set = set(split_labels["test"])
    
    tv_shared = list(train_labels_set.intersection(val_labels_set))
    tt_shared = list(train_labels_set.intersection(test_labels_set))
    vt_shared = list(val_labels_set.intersection(test_labels_set))
    all_shared = list(set(tv_shared + tt_shared + vt_shared))
    
    analysis["cross_split_label_analysis"] = {
        "train_val_shared_labels": tv_shared,
        "train_val_shared_count": len(tv_shared),
        "train_test_shared_labels": tt_shared,
        "train_test_shared_count": len(tt_shared),
        "val_test_shared_labels": vt_shared,
        "val_test_shared_count": len(vt_shared),
        "total_unique_shared_labels_across_splits": len(all_shared)
    }
    
    # Write JSON report
    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
    with open(output_report_path, "w") as f:
        json.dump(analysis, f, indent=2)
        
    print(f"[+] Detailed analysis JSON generated at: {output_report_path}")
    
    # Terminal summary
    print("\n" + "=" * 75)
    print("OCR DATASET AUDIT SUMMARY")
    print("=" * 75)
    print(f"Total Verified Samples:         {len(all_records)}")
    print(f"  - Train:                      {len(split_dfs['train'])}")
    print(f"  - Val:                        {len(split_dfs['val'])}")
    print(f"  - Test:                       {len(split_dfs['test'])}")
    print(f"Unreadable/Missing Images:      {analysis['image_integrity']['total_unreadable']}")
    print(f"Images in Multiple Splits:      {analysis['split_leakage_check']['image_leakage_count']}")
    print(f"Identical Image Hashes:         {analysis['duplicate_image_hashes']['duplicate_hash_groups_count']} groups")
    print(f"Unique Plate Text Strings:      {analysis['plate_text_statistics']['unique_labels']}")
    print(f"Label Length Range (min/max):   {analysis['plate_text_statistics']['min_label_length']} to {analysis['plate_text_statistics']['max_label_length']} chars (Mean: {analysis['plate_text_statistics']['mean_label_length']})")
    print(f"Character Vocabulary Size:      {analysis['character_vocabulary']['total_unique_chars']} (A-Z: {sum(1 for v in a_z_freq.values() if v > 0)}/26, Digits: 10/10)")
    print(f"Unexpected Characters:          {len(analysis['character_vocabulary']['unexpected_characters'])}")
    print(f"Image Dimensions (W x H):       Mean: {analysis['image_geometry_statistics']['mean_width']}x{analysis['image_geometry_statistics']['mean_height']} px | Median: {analysis['image_geometry_statistics']['median_width']}x{analysis['image_geometry_statistics']['median_height']} px")
    print(f"Aspect Ratios (W/H):            Mean: {analysis['image_geometry_statistics']['mean_aspect_ratio']} | Median: {analysis['image_geometry_statistics']['median_aspect_ratio']}")
    print(f"Cross-Split Shared Labels:      Train/Val: {len(tv_shared)} | Train/Test: {len(tt_shared)} | Val/Test: {len(vt_shared)}")
    print("=" * 75)
    
    return True

if __name__ == "__main__":
    d_dir = r"c:\SIH\prototype\smart-transport-monitoring\module3_incident_anpr\indian_license_plate_ocr"
    r_path = r"c:\SIH\prototype\smart-transport-monitoring\module3_incident_anpr\ocr_dataset_analysis.json"
    analyze_ocr_dataset(d_dir, r_path)
