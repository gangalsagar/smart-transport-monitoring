#!/usr/bin/env python3
"""
Compare CTC Decoding Strategies: Greedy vs CTC Prefix Beam Search
================================================================
Compares:
- ocr_test_results_greedy.json
- ocr_test_results_beam.json

Outputs comprehensive comparison metrics:
- Exact Plate Accuracy
- Character Accuracy
- Character Error Rate (CER)
- Latency benchmarks
- Deletions, Substitutions, Insertions
- Prediction length distributions
- Saves machine-readable summary to ocr_decoder_comparison.json
"""

import sys
import json
from pathlib import Path

# Import shared alignment logic from analyze_ocr_errors
sys.path.append(str(Path("module3_incident_anpr").resolve()))
from analyze_ocr_errors import analyze_experiment

def compare_decoders(
    greedy_results_path="module3_incident_anpr/ocr_test_results_greedy.json",
    beam_results_path="module3_incident_anpr/ocr_test_results_beam.json",
    output_path="module3_incident_anpr/ocr_decoder_comparison.json"
):
    greedy_file = Path(greedy_results_path)
    beam_file = Path(beam_results_path)

    if not greedy_file.exists():
        print(f"[-] ERROR: Missing greedy results: {greedy_file}")
        sys.exit(1)
    if not beam_file.exists():
        print(f"[-] ERROR: Missing beam search results: {beam_file}")
        sys.exit(1)

    greedy_data = json.load(open(greedy_file))
    beam_data = json.load(open(beam_file))

    g_ana = analyze_experiment(greedy_data)
    b_ana = analyze_experiment(beam_data)

    g_m = g_ana["metrics"]
    b_m = b_ana["metrics"]

    g_err = g_ana["error_classification"]
    b_err = b_ana["error_classification"]

    g_len = g_ana["length_analysis"]
    b_len = b_ana["length_analysis"]

    # Sample-level comparison
    g_preds = {p["image"]: p for p in greedy_data["predictions"]}
    b_preds = {p["image"]: p for p in beam_data["predictions"]}

    beam_fixed = []
    beam_broke = []

    for img, g_p in g_preds.items():
        b_p = b_preds.get(img)
        if not b_p:
            continue

        g_ok = g_p["exact_match"]
        b_ok = b_p["exact_match"]

        if not g_ok and b_ok:
            beam_fixed.append({
                "image": img,
                "ground_truth": g_p["ground_truth"],
                "greedy_pred": g_p["prediction"],
                "beam_pred": b_p["prediction"]
            })
        elif g_ok and not b_ok:
            beam_broke.append({
                "image": img,
                "ground_truth": g_p["ground_truth"],
                "greedy_pred": g_p["prediction"],
                "beam_pred": b_p["prediction"]
            })

    report = {
        "metrics_comparison": {
            "greedy": g_m,
            "beam_search": b_m,
            "delta_beam_minus_greedy": {
                "exact_plate_accuracy": round(b_m.get("exact_plate_accuracy", 0) - g_m.get("exact_plate_accuracy", 0), 4),
                "character_accuracy": round(b_m.get("character_accuracy", 0) - g_m.get("character_accuracy", 0), 4),
                "character_error_rate_cer": round(b_m.get("character_error_rate_cer", 0) - g_m.get("character_error_rate_cer", 0), 4),
                "avg_cpu_latency_ms": round(b_m.get("average_cpu_latency_ms", 0) - g_m.get("average_cpu_latency_ms", 0), 2)
            }
        },
        "error_decomposition_comparison": {
            "greedy_errors": g_err,
            "beam_errors": b_err,
            "difference": {
                "total_errors": b_err["total_errors"] - g_err["total_errors"],
                "substitutions": b_err["substitutions"]["count"] - g_err["substitutions"]["count"],
                "deletions": b_err["deletions_missing_chars"]["count"] - g_err["deletions_missing_chars"]["count"],
                "insertions": b_err["insertions_extra_chars"]["count"] - g_err["insertions_extra_chars"]["count"]
            }
        },
        "length_distribution_comparison": {
            "greedy": g_len,
            "beam_search": b_len
        },
        "sample_disagreements": {
            "beam_fixed_count": len(beam_fixed),
            "beam_broke_count": len(beam_broke),
            "beam_fixed_samples": beam_fixed,
            "beam_broke_samples": beam_broke
        }
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print("=" * 80)
    print("CTC DECODER COMPARISON: GREEDY vs PREFIX BEAM SEARCH (WIDTH=10)")
    print("=" * 80)
    print(f"{'Metric':<30} | {'Greedy Decoder':<20} | {'Beam Search Decoder':<20} | {'Delta (Beam - Greedy)'}")
    print("-" * 80)
    print(f"{'Exact Plate Accuracy':<30} | {g_m.get('exact_plate_accuracy', 0):<20.2%} | {b_m.get('exact_plate_accuracy', 0):<20.2%} | {(b_m.get('exact_plate_accuracy', 0) - g_m.get('exact_plate_accuracy', 0)):+.2%}")
    print(f"{'Character Accuracy':<30} | {g_m.get('character_accuracy', 0):<20.2%} | {b_m.get('character_accuracy', 0):<20.2%} | {(b_m.get('character_accuracy', 0) - g_m.get('character_accuracy', 0)):+.2%}")
    print(f"{'Character Error Rate (CER)':<30} | {g_m.get('character_error_rate_cer', 0):<20.4f} | {b_m.get('character_error_rate_cer', 0):<20.4f} | {(b_m.get('character_error_rate_cer', 0) - g_m.get('character_error_rate_cer', 0)):+.4f}")
    print(f"{'Avg CPU Latency per Crop':<30} | {g_m.get('average_cpu_latency_ms', 0):<17.2f} ms | {b_m.get('average_cpu_latency_ms', 0):<17.2f} ms | {(b_m.get('average_cpu_latency_ms', 0) - g_m.get('average_cpu_latency_ms', 0)):+.2f} ms")
    print(f"{'Median CPU Latency per Crop':<30} | {g_m.get('median_cpu_latency_ms', 0):<17.2f} ms | {b_m.get('median_cpu_latency_ms', 0):<17.2f} ms | {(b_m.get('median_cpu_latency_ms', 0) - g_m.get('median_cpu_latency_ms', 0)):+.2f} ms")

    print("\n" + "=" * 80)
    print("ERROR DECOMPOSITION DIFFERENCE")
    print("=" * 80)
    print(f"Total Errors:      Greedy = {g_err['total_errors']} | Beam = {b_err['total_errors']} (Diff: {b_err['total_errors'] - g_err['total_errors']:+d})")
    print(f"  - Substitutions: Greedy = {g_err['substitutions']['count']} ({g_err['substitutions']['percentage_of_errors']}%) | Beam = {b_err['substitutions']['count']} ({b_err['substitutions']['percentage_of_errors']}%) | Diff: {b_err['substitutions']['count'] - g_err['substitutions']['count']:+d}")
    print(f"  - Deletions:     Greedy = {g_err['deletions_missing_chars']['count']} ({g_err['deletions_missing_chars']['percentage_of_errors']}%) | Beam = {b_err['deletions_missing_chars']['count']} ({b_err['deletions_missing_chars']['percentage_of_errors']}%) | Diff: {b_err['deletions_missing_chars']['count'] - g_err['deletions_missing_chars']['count']:+d}")
    print(f"  - Insertions:    Greedy = {g_err['insertions_extra_chars']['count']} ({g_err['insertions_extra_chars']['percentage_of_errors']}%) | Beam = {b_err['insertions_extra_chars']['count']} ({b_err['insertions_extra_chars']['percentage_of_errors']}%) | Diff: {b_err['insertions_extra_chars']['count'] - g_err['insertions_extra_chars']['count']:+d}")

    print("\n" + "=" * 80)
    print("PREDICTION LENGTH RESIDUAL COMPARISON")
    print("=" * 80)
    print(f"Greedy: Same Length = {g_len['distribution']['same_length']} ({g_len['distribution_percentages']['same_length']}%), Shorter = {g_len['distribution']['shorter_prediction']} ({g_len['distribution_percentages']['shorter_prediction']}%), Longer = {g_len['distribution']['longer_prediction']} ({g_len['distribution_percentages']['longer_prediction']}%)")
    print(f"Beam:   Same Length = {b_len['distribution']['same_length']} ({b_len['distribution_percentages']['same_length']}%), Shorter = {b_len['distribution']['shorter_prediction']} ({b_len['distribution_percentages']['shorter_prediction']}%), Longer = {b_len['distribution']['longer_prediction']} ({b_len['distribution_percentages']['longer_prediction']}%)")
    print(f"Mean Length Residual: Greedy = {g_len['mean_length_residual']} chars | Beam = {b_len['mean_length_residual']} chars")

    print("\n" + "=" * 80)
    print(f"Detailed Decoder Comparison saved to: {output_path}")
    print("=" * 80)

if __name__ == "__main__":
    compare_decoders()
