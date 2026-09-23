import sys
import json
from pathlib import Path

# Add module path
sys.path.append(str(Path("module3_incident_anpr").resolve()))
from analyze_ocr_errors import analyze_experiment

def compare():
    base_file = Path("module3_incident_anpr/ocr_test_results.json")
    v2_file = Path("module3_incident_anpr/ocr_test_results_arch_v2.json")

    base_data = json.load(open(base_file))
    v2_data = json.load(open(v2_file))

    base_ana = analyze_experiment(base_data)
    v2_ana = analyze_experiment(v2_data)

    print("=" * 80)
    print("METRIC COMPARISON: BASELINE vs ARCHITECTURE V2")
    print("=" * 80)
    print(f"{'Metric':<30} | {'Baseline (48x160)':<20} | {'Arch V2 (48x224)':<20} | {'Delta (V2 - Base)'}")
    print("-" * 80)
    
    b_acc = base_ana['metrics']['exact_plate_accuracy']
    v_acc = v2_ana['metrics']['exact_plate_accuracy']
    print(f"{'Exact Plate Accuracy':<30} | {b_acc:<20.2%} | {v_acc:<20.2%} | {(v_acc - b_acc):+.2%}")

    b_cacc = base_ana['metrics']['character_accuracy']
    v_cacc = v2_ana['metrics']['character_accuracy']
    print(f"{'Character Accuracy':<30} | {b_cacc:<20.2%} | {v_cacc:<20.2%} | {(v_cacc - b_cacc):+.2%}")

    b_cer = base_ana['metrics']['character_error_rate_cer']
    v_cer = v2_ana['metrics']['character_error_rate_cer']
    print(f"{'Character Error Rate (CER)':<30} | {b_cer:<20.4f} | {v_cer:<20.4f} | {(v_cer - b_cer):+.4f}")

    b_lat = base_ana['metrics']['average_cpu_latency_ms']
    v_lat = v2_ana['metrics']['average_cpu_latency_ms']
    print(f"{'Avg CPU Latency per Crop':<30} | {b_lat:<20.2f} ms | {v_lat:<20.2f} ms | {(v_lat - b_lat):+.2f} ms")

    print("\n" + "=" * 80)
    print("ERROR DECOMPOSITION COMPARISON")
    print("=" * 80)
    b_err = base_ana['error_classification']
    v_err = v2_ana['error_classification']
    print(f"Total Errors: Baseline = {b_err['total_errors']} | Arch V2 = {v_err['total_errors']}")
    print(f"  - Substitutions: Baseline = {b_err['substitutions']['count']} ({b_err['substitutions']['percentage_of_errors']}%) | Arch V2 = {v_err['substitutions']['count']} ({v_err['substitutions']['percentage_of_errors']}%)")
    print(f"  - Deletions:     Baseline = {b_err['deletions_missing_chars']['count']} ({b_err['deletions_missing_chars']['percentage_of_errors']}%) | Arch V2 = {v_err['deletions_missing_chars']['count']} ({v_err['deletions_missing_chars']['percentage_of_errors']}%)")
    print(f"  - Insertions:    Baseline = {b_err['insertions_extra_chars']['count']} ({b_err['insertions_extra_chars']['percentage_of_errors']}%) | Arch V2 = {v_err['insertions_extra_chars']['count']} ({v_err['insertions_extra_chars']['percentage_of_errors']}%)")

    print("\n" + "=" * 80)
    print("PREDICTION LENGTH RESIDUALS")
    print("=" * 80)
    b_len = base_ana['length_analysis']
    v_len = v2_ana['length_analysis']
    print(f"Baseline: Same Length = {b_len['distribution']['same_length']} ({b_len['distribution_percentages']['same_length']}%), Shorter = {b_len['distribution']['shorter_prediction']} ({b_len['distribution_percentages']['shorter_prediction']}%), Longer = {b_len['distribution']['longer_prediction']} ({b_len['distribution_percentages']['longer_prediction']}%)")
    print(f"Arch V2:  Same Length = {v_len['distribution']['same_length']} ({v_len['distribution_percentages']['same_length']}%), Shorter = {v_len['distribution']['shorter_prediction']} ({v_len['distribution_percentages']['shorter_prediction']}%), Longer = {v_len['distribution']['longer_prediction']} ({v_len['distribution_percentages']['longer_prediction']}%)")
    print(f"Mean Length Residual: Baseline = {b_len['mean_length_residual']} chars | Arch V2 = {v_len['mean_length_residual']} chars")

if __name__ == "__main__":
    compare()
