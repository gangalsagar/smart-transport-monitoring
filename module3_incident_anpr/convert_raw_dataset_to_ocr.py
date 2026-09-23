#!/usr/bin/env python3
"""
Convert Raw Pascal VOC Indian License Plate Dataset to Module 3 OCR Format
===========================================================================
Extracts cropped number plates from raw vehicle images and pairs each crop
with its ground truth plate transcription from Pascal VOC XML annotations.

Features:
- Robust multi-extension image resolver (.jpg, .jpeg, .png, case-insensitive)
- Bounding box validation, clamping, and zero-area rejection
- OCR text cleaning and validation (strict Indian alphanumeric chars)
- Deduplication and deterministic train/val/test splits (80/10/10)
- Preserves raw source dataset untouched
- Outputs labels.csv, train.csv, val.csv, test.csv, and conversion_report.json
"""

import os
import re
import sys
import glob
import json
import random
import xml.etree.ElementTree as ET
from PIL import Image
import pandas as pd

def clean_plate_text(text: str) -> str:
    """Clean and normalize OCR plate text to uppercase alphanumeric."""
    if not text:
        return ""
    # Strip whitespace, dashes, dots, underscores
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text).upper()
    return cleaned

def resolve_image_file(xml_path: str, xml_filename_tag: str, search_dir: str):
    """
    Robustly locate the corresponding image file given the XML path and internal tag.
    Tries multiple strategies:
    1. Direct match with tag in same directory
    2. Stem match with XML file name in same directory
    3. Extensions: .jpg, .jpeg, .png, .JPG, .JPEG, .PNG
    """
    dir_path = os.path.dirname(xml_path)
    xml_stem = os.path.splitext(os.path.basename(xml_path))[0]
    
    candidates = []
    
    # Check filename from XML tag
    if xml_filename_tag:
        tag_basename = os.path.basename(xml_filename_tag.strip())
        candidates.append(os.path.join(dir_path, tag_basename))
        tag_stem = os.path.splitext(tag_basename)[0]
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
            candidates.append(os.path.join(dir_path, tag_stem + ext))
            
    # Check XML stem name
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
        candidates.append(os.path.join(dir_path, xml_stem + ext))
        
    # Check if xml_stem ends with double extensions like file.jpg.xml -> file.jpg
    if xml_stem.lower().endswith(('.jpg', '.jpeg', '.png')):
        candidates.append(os.path.join(dir_path, xml_stem))

    for cand in candidates:
        if os.path.isfile(cand):
            return cand
            
    return None

def convert_dataset(
    raw_dataset_dir: str,
    output_dir: str,
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    random_seed: int = 42
):
    print("=" * 75)
    print("CONVERTING RAW INDIAN ANPR DATASET TO MODULE 3 OCR DATASET")
    print(f"Source: {raw_dataset_dir}")
    print(f"Target: {output_dir}")
    print("=" * 75)
    
    os.makedirs(output_dir, exist_ok=True)
    images_out_dir = os.path.join(output_dir, "images")
    os.makedirs(images_out_dir, exist_ok=True)
    
    report = {
        "raw_source_dir": raw_dataset_dir,
        "output_dir": output_dir,
        "total_xml_files": 0,
        "total_images_found": 0,
        "successful_ocr_samples": 0,
        "train_samples": 0,
        "val_samples": 0,
        "test_samples": 0,
        "missing_images": 0,
        "corrupted_images": 0,
        "invalid_xml": 0,
        "invalid_bounding_boxes": 0,
        "invalid_labels": 0,
        "duplicate_samples": 0,
        "rejected_samples": 0,
        "rejected_details": []
    }
    
    # 1. Discover all XML files recursively
    xml_files = glob.glob(os.path.join(raw_dataset_dir, "**", "*.xml"), recursive=True)
    report["total_xml_files"] = len(xml_files)
    print(f"[+] Found {len(xml_files)} Pascal VOC XML files across subdirectories.")
    
    samples = []
    seen_hashes = set()
    resolved_images = set()
    sample_counter = 1
    
    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
        except Exception as e:
            report["invalid_xml"] += 1
            report["rejected_samples"] += 1
            report["rejected_details"].append({"file": xml_file, "reason": f"XML Parse Error: {e}"})
            continue
            
        filename_tag = root.findtext("filename", "")
        img_path = resolve_image_file(xml_file, filename_tag, raw_dataset_dir)
        
        if not img_path or not os.path.exists(img_path):
            report["missing_images"] += 1
            report["rejected_samples"] += 1
            report["rejected_details"].append({"file": xml_file, "reason": f"Missing image for tag '{filename_tag}'"})
            continue
            
        try:
            orig_img = Image.open(img_path)
            orig_img.verify()
            # Reopen for cropping after verify
            orig_img = Image.open(img_path)
            img_w, img_h = orig_img.size
        except Exception as e:
            report["corrupted_images"] += 1
            report["rejected_samples"] += 1
            report["rejected_details"].append({"file": img_path, "reason": f"Corrupted image: {e}"})
            continue
            
        # Track resolved source image
        resolved_images.add(img_path)
        report["total_images_found"] = len(resolved_images)
            
        # Inspect all objects in XML
        for obj in root.findall("object"):
            raw_text = obj.findtext("name", "").strip()
            cleaned_text = clean_plate_text(raw_text)
            
            # Label validation
            if not cleaned_text or len(cleaned_text) < 4:
                report["invalid_labels"] += 1
                report["rejected_samples"] += 1
                report["rejected_details"].append({"file": xml_file, "raw_label": raw_text, "reason": "Invalid/empty text label"})
                continue
                
            bndbox = obj.find("bndbox")
            if bndbox is None:
                report["invalid_bounding_boxes"] += 1
                report["rejected_samples"] += 1
                report["rejected_details"].append({"file": xml_file, "reason": "No bndbox element in object"})
                continue
                
            try:
                xmin = float(bndbox.findtext("xmin"))
                ymin = float(bndbox.findtext("ymin"))
                xmax = float(bndbox.findtext("xmax"))
                ymax = float(bndbox.findtext("ymax"))
            except Exception as e:
                report["invalid_bounding_boxes"] += 1
                report["rejected_samples"] += 1
                report["rejected_details"].append({"file": xml_file, "reason": f"Bndbox coordinate error: {e}"})
                continue
                
            # Clamp coordinates
            xmin = max(0, min(int(round(xmin)), img_w - 1))
            ymin = max(0, min(int(round(ymin)), img_h - 1))
            xmax = max(0, min(int(round(xmax)), img_w))
            ymax = max(0, min(int(round(ymax)), img_h))
            
            crop_w = xmax - xmin
            crop_h = ymax - ymin
            
            if crop_w < 10 or crop_h < 10:
                report["invalid_bounding_boxes"] += 1
                report["rejected_samples"] += 1
                report["rejected_details"].append({"file": xml_file, "box": [xmin, ymin, xmax, ymax], "reason": f"Invalid crop dimensions ({crop_w}x{crop_h})"})
                continue
                
            # Crop plate
            try:
                crop_img = orig_img.crop((xmin, ymin, xmax, ymax))
                # Ensure RGB mode
                if crop_img.mode != 'RGB':
                    crop_img = crop_img.convert('RGB')
            except Exception as e:
                report["corrupted_images"] += 1
                report["rejected_samples"] += 1
                report["rejected_details"].append({"file": img_path, "reason": f"Crop failure: {e}"})
                continue
                
            # Check duplicates based on image stem + text
            dedup_key = f"{os.path.basename(img_path)}_{cleaned_text}_{xmin}_{ymin}"
            if dedup_key in seen_hashes:
                report["duplicate_samples"] += 1
                report["rejected_samples"] += 1
                continue
            seen_hashes.add(dedup_key)
            
            # Save cropped plate
            out_filename = f"plate_{sample_counter:06d}.jpg"
            out_filepath = os.path.join(images_out_dir, out_filename)
            crop_img.save(out_filepath, "JPEG", quality=95)
            
            # Track sample
            source_folder = os.path.basename(os.path.dirname(xml_file))
            samples.append({
                "image": out_filename,
                "text": cleaned_text,
                "source_group": f"{source_folder}_{os.path.basename(img_path)}"
            })
            sample_counter += 1

    report["successful_ocr_samples"] = len(samples)
    print(f"[+] Successfully extracted and verified {len(samples)} OCR plate crops.")
    
    # Deterministic Split by source group to avoid leakage
    random.seed(random_seed)
    
    # Group samples by source image to ensure multiple crops from same vehicle don't leak across splits
    groups = {}
    for s in samples:
        grp = s["source_group"]
        if grp not in groups:
            groups[grp] = []
        groups[grp].append(s)
        
    group_keys = list(groups.keys())
    random.shuffle(group_keys)
    
    total_grps = len(group_keys)
    train_end = int(total_grps * train_ratio)
    val_end = int(total_grps * (train_ratio + val_ratio))
    
    train_groups = set(group_keys[:train_end])
    val_groups = set(group_keys[train_end:val_end])
    test_groups = set(group_keys[val_end:])
    
    train_samples = []
    val_samples = []
    test_samples = []
    
    for s in samples:
        grp = s["source_group"]
        if grp in train_groups:
            train_samples.append({"image": s["image"], "text": s["text"]})
        elif grp in val_groups:
            val_samples.append({"image": s["image"], "text": s["text"]})
        else:
            test_samples.append({"image": s["image"], "text": s["text"]})
            
    report["train_samples"] = len(train_samples)
    report["val_samples"] = len(val_samples)
    report["test_samples"] = len(test_samples)
    
    # Save CSV files
    all_df = pd.DataFrame([{"image": s["image"], "text": s["text"]} for s in samples])
    train_df = pd.DataFrame(train_samples)
    val_df = pd.DataFrame(val_samples)
    test_df = pd.DataFrame(test_samples)
    
    all_df.to_csv(os.path.join(output_dir, "labels.csv"), index=False)
    train_df.to_csv(os.path.join(output_dir, "train.csv"), index=False)
    val_df.to_csv(os.path.join(output_dir, "val.csv"), index=False)
    test_df.to_csv(os.path.join(output_dir, "test.csv"), index=False)
    
    # Save report
    report_path = os.path.join(output_dir, "conversion_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print("\n" + "=" * 75)
    print("CONVERSION SUMMARY REPORT")
    print("=" * 75)
    print(f"Total XML Files Scanned:    {report['total_xml_files']}")
    print(f"Successful OCR Crops:       {report['successful_ocr_samples']}")
    print(f"  - Train Split (80%):      {report['train_samples']}")
    print(f"  - Val Split (10%):        {report['val_samples']}")
    print(f"  - Test Split (10%):       {report['test_samples']}")
    print(f"Missing Images:             {report['missing_images']}")
    print(f"Invalid XML Files:          {report['invalid_xml']}")
    print(f"Invalid Bounding Boxes:     {report['invalid_bounding_boxes']}")
    print(f"Invalid/Empty Labels:       {report['invalid_labels']}")
    print(f"Duplicate Samples Dropped:  {report['duplicate_samples']}")
    print(f"Total Rejected Samples:     {report['rejected_samples']}")
    print(f"Report Written To:          {report_path}")
    print("=" * 75)

if __name__ == "__main__":
    src = r"C:\Users\SAGAR GANGAL\OneDrive\Desktop\module 3 number 3"
    dst = r"C:\SIH\prototype\smart-transport-monitoring\module3_incident_anpr\indian_license_plate_ocr"
    convert_dataset(src, dst)
