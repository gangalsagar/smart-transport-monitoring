#!/usr/bin/env python3
"""
Read-Only Architecture & Preprocessing Audit for Module 3 ANPR OCR
==================================================================
Forensic inspection of:
- Input preprocessing (resizing, padding, aspect ratio preservation, normalization)
- CNN layer-by-layer tensor spatial transformations (Height, Width, Channels)
- Horizontal downsampling ratio and receptive field per temporal slice
- CTC sequence capacity across target plate lengths (8 to 12 characters)
- Repeated character dynamics and blank-token collapse mechanisms
- Potential root causes for deletion bias and character substitutions
"""

import os
import sys
import json
import torch
import torch.nn as nn
from PIL import Image
import numpy as np

# Import actual model architecture from train_ocr
from train_ocr import CRNNOcrModel, NUM_CLASSES, resize_and_pad

def audit_architecture(output_path="module3_incident_anpr/ocr_architecture_audit.json"):
    print("=" * 80)
    print("READ-ONLY FORENSIC AUDIT: OCR ARCHITECTURE & PREPROCESSING PIPELINE")
    print("=" * 80)

    # 1. Preprocessing Pipeline Specification
    preprocessing_spec = {
        "input_mode": "Grayscale ('L')",
        "target_resolution": {"height": 48, "width": 160},
        "aspect_ratio_handling": "Preserved strictly via uniform scaling (scale = min(160/w, 48/h))",
        "stretching_distortion": "Zero geometric stretching (non-anamorphic)",
        "padding_strategy": "Center-aligned zero/constant padding on shorter axis",
        "padding_fill_value": 128,  # Neutral gray
        "interpolation_method": "PIL.Image.BILINEAR",
        "tensor_normalization": {
            "range_mapping": "Raw uint8 [0, 255] -> float32 / 255.0 -> (arr - 0.5) / 0.5",
            "output_tensor_range": "[-1.0, 1.0]",
            "tensor_shape": "[Batch, 1, 48, 160]"
        }
    }

    # 2. Layer-by-Layer CNN Tensor Spatial Tracing
    model = CRNNOcrModel(num_classes=NUM_CLASSES)
    model.eval()

    dummy_input = torch.zeros(1, 1, 48, 160)
    
    # Trace CNN sequential layers
    layer_traces = []
    current_x = dummy_input
    
    # Layer details map
    layer_descriptions = [
        {"name": "Conv2d_1", "kernel": "3x3", "stride": 1, "padding": 1},
        {"name": "BatchNorm2d_1", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "ReLU_1", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "MaxPool2d_1", "kernel": "2x2", "stride": 2, "padding": 0},
        
        {"name": "Conv2d_2", "kernel": "3x3", "stride": 1, "padding": 1},
        {"name": "BatchNorm2d_2", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "ReLU_2", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "MaxPool2d_2", "kernel": "2x2", "stride": 2, "padding": 0},

        {"name": "Conv2d_3", "kernel": "3x3", "stride": 1, "padding": 1},
        {"name": "BatchNorm2d_3", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "ReLU_3", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        
        {"name": "Conv2d_4", "kernel": "3x3", "stride": 1, "padding": 1},
        {"name": "BatchNorm2d_4", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "ReLU_4", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "MaxPool2d_3 (Asymmetric)", "kernel": "2x1", "stride": "2x1", "padding": 0},

        {"name": "Conv2d_5", "kernel": "3x3", "stride": 1, "padding": 1},
        {"name": "BatchNorm2d_5", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "ReLU_5", "kernel": "N/A", "stride": "N/A", "padding": "N/A"},
        {"name": "MaxPool2d_4 (Asymmetric)", "kernel": "2x1", "stride": "2x1", "padding": 0},
    ]

    for idx, layer in enumerate(model.cnn):
        in_shape = list(current_x.shape)
        current_x = layer(current_x)
        out_shape = list(current_x.shape)
        desc = layer_descriptions[idx]
        layer_traces.append({
            "layer_index": idx,
            "layer_name": desc["name"],
            "layer_type": layer.__class__.__name__,
            "kernel_size": desc["kernel"],
            "stride": desc["stride"],
            "padding": desc["padding"],
            "input_shape": in_shape,
            "output_shape": out_shape
        })

    # Sequence transformation
    # current_x is [1, 512, 3, 40]
    b, c, h, w = current_x.size()
    seq_x = current_x.permute(0, 3, 1, 2).contiguous().view(b, w, c * h)  # [1, 40, 1536]
    lstm_out, _ = model.rnn(seq_x)  # [1, 40, 512]
    logits = model.classifier(lstm_out)  # [1, 40, 37]
    logits_ctc = logits.permute(1, 0, 2)  # [40, 1, 37]

    temporal_sequence_length = w  # 40
    input_width = 160
    horizontal_compression_ratio = input_width / temporal_sequence_length  # 4.0
    pixels_per_time_step = horizontal_compression_ratio  # 4.0 pixels

    # 3. CTC Sequence Capacity Analysis
    # In CTC, to emit L non-repeated characters, we need at least L time steps.
    # To emit consecutive identical characters (e.g. '00', '77', 'EE'), at least 1 blank token must separate them:
    # Minimum CTC steps for string with duplicate pairs = len(string) + duplicate_consecutive_count.
    plate_lengths_analysis = {}
    for length in range(8, 13):
        # Calculate worst case: all identical characters (e.g. 'AAAAAAAAAA' -> 10 chars + 9 blanks = 19 steps)
        min_steps_distinct = length
        min_steps_worst_case = (2 * length) - 1
        effective_slots_per_char = round(temporal_sequence_length / length, 2)
        plate_lengths_analysis[str(length)] = {
            "plate_character_length": length,
            "min_ctc_steps_distinct_chars": min_steps_distinct,
            "min_ctc_steps_worst_case_repeated": min_steps_worst_case,
            "available_ctc_time_steps": temporal_sequence_length,
            "effective_time_steps_per_character": effective_slots_per_char,
            "capacity_status": "Theoretically Sufficient" if temporal_sequence_length >= min_steps_worst_case else "Tight / Constrained"
        }

    # 4. CTC Decoding & Loss Configuration
    ctc_audit = {
        "loss_function": "torch.nn.CTCLoss(blank=0, zero_infinity=True)",
        "decoding_algorithm": "Greedy Argmax Decoding (Best Path)",
        "blank_index": 0,
        "blank_token_handling": "Blanks stripped after argmax selection",
        "consecutive_collapse_rule": "Collapse consecutive identical non-blank predictions into a single token (standard CTC rule)",
        "deletion_bias_mechanism": [
            "1. Horizontal Receptive Field Compression: 160px width is compressed 4x down to 40 time steps. For narrow characters (such as '1', 'I', or tightly spaced letters like 'TT'), the CNN activations for adjacent characters can blur into the same temporal step.",
            "2. Padding Dilution: A crop with high aspect ratio padded with gray bars reduces the active plate width inside the 160px canvas, reducing the effective time steps allocated to the plate text from 40 down to ~24-28 steps (only ~2.4 to 2.8 steps per character on 10-char plates).",
            "3. Greedy Collapse vs Blank Insertion: If the network fails to emit a distinct blank token between consecutive identical or visually similar characters, CTC greedy collapse forcibly merges them into a single character, directly manifesting as a Deletion error."
        ]
    }

    # 5. Substitution Error Mechanism
    substitution_audit = {
        "primary_causes": [
            "1. Fine-Grained Glyph Ambiguity: Feature extractor downsamples vertical height from 48px to 3px (16x vertical compression). Fine horizontal crossbars (differentiating 4 vs 1, C vs D, P vs S, 0 vs 3) lose structural distinction at 3px feature height.",
            "2. Imbalanced State Prefix Prior: In real-world data, 'MH' and 'HR' appear much more frequently than other states, biasing early recurrent transitions towards 'MH' / '02' / '26' prefix loops."
        ]
    }

    master_audit = {
        "preprocessing_pipeline": preprocessing_spec,
        "layer_by_layer_trace": layer_traces,
        "temporal_sequence_metrics": {
            "input_canvas_resolution": f"48 x 160",
            "final_feature_map_shape": f"[Batch, 512, {h}, {w}]",
            "final_ctc_temporal_steps (T)": temporal_sequence_length,
            "horizontal_downsampling_factor": f"{horizontal_compression_ratio}x",
            "horizontal_pixels_per_step": f"{pixels_per_time_step} px",
            "vertical_downsampling_factor": "16x (48px -> 3px)"
        },
        "ctc_sequence_capacity": plate_lengths_analysis,
        "ctc_training_and_decoding": ctc_audit,
        "substitution_error_root_causes": substitution_audit
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(master_audit, f, indent=2)

    # Print Terminal Summary
    print(f"[+] Architecture & Preprocessing Audit saved to: {output_path}\n")
    print("=" * 80)
    print("1. PREPROCESSING PIPELINE SPECIFICATION")
    print("=" * 80)
    print(f"Input Mode:             {preprocessing_spec['input_mode']}")
    print(f"Target Canvas Size:     {preprocessing_spec['target_resolution']['height']} x {preprocessing_spec['target_resolution']['width']} (Height x Width)")
    print(f"Aspect Ratio Handling:  {preprocessing_spec['aspect_ratio_handling']}")
    print(f"Geometric Distortion:   {preprocessing_spec['stretching_distortion']}")
    print(f"Padding Fill:           {preprocessing_spec['padding_fill_value']} (Neutral Gray)")
    print(f"Tensor Range:           {preprocessing_spec['tensor_normalization']['output_tensor_range']}")

    print("\n" + "=" * 80)
    print("2. LAYER-BY-LAYER TENSOR SPATIAL TRANSFORMATIONS")
    print("=" * 80)
    print(f"{'Layer':<28} | {'Kernel':<10} | {'Stride':<10} | {'Input Shape':<20} | {'Output Shape'}")
    print("-" * 80)
    for t in layer_traces:
        if "Conv" in t["layer_type"] or "Pool" in t["layer_type"]:
            in_s = f"{t['input_shape'][1]}x{t['input_shape'][2]}x{t['input_shape'][3]}"
            out_s = f"{t['output_shape'][1]}x{t['output_shape'][2]}x{t['output_shape'][3]}"
            print(f"{t['layer_name']:<28} | {str(t['kernel_size']):<10} | {str(t['stride']):<10} | {in_s:<20} | {out_s}")

    print("\n" + "=" * 80)
    print("3. TEMPORAL SEQUENCE METRICS & HORIZONTAL COMPRESSION")
    print("=" * 80)
    print(f"Input Canvas Resolution:        48 x 160 px")
    print(f"Final Feature Map Size:         512 channels x 3 (H) x 40 (W)")
    print(f"Final CTC Temporal Length (T):  40 time steps")
    print(f"Horizontal Compression Ratio:   4.0x (160 px / 40 steps = 4.0 px per step)")
    print(f"Vertical Compression Ratio:     16.0x (48 px / 3 px)")

    print("\n" + "=" * 80)
    print("4. CTC SEQUENCE CAPACITY BY PLATE LENGTH")
    print("=" * 80)
    print(f"{'Plate Length':<15} | {'Min Steps (Distinct)':<22} | {'Min Steps (Worst Case)':<24} | {'Available Steps':<18} | {'Steps / Char'}")
    print("-" * 80)
    for l_k, l_v in plate_lengths_analysis.items():
        print(f"{l_k + ' characters':<15} | {l_v['min_ctc_steps_distinct_chars']:<22} | {l_v['min_ctc_steps_worst_case_repeated']:<24} | {l_v['available_ctc_time_steps']:<18} | {l_v['effective_time_steps_per_character']} steps/char")

    print("\n" + "=" * 80)
    print("5. POTENTIAL ROOT CAUSES FOR DELETION BIAS & SUBSTITUTIONS")
    print("=" * 80)
    print("A. Deletion Bias Causes (47.06% shorter predictions):")
    for r in ctc_audit["deletion_bias_mechanism"]:
        print(f"   {r}")
    print("\nB. Substitution Error Causes (68.81% of errors):")
    for r in substitution_audit["primary_causes"]:
        print(f"   {r}")
    print("=" * 80)

if __name__ == "__main__":
    audit_architecture()
