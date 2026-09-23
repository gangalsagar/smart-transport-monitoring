from pathlib import Path
from ultralytics import YOLO
import torch


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "runs"
    / "detect"
    / "module1_road_defect"
    / "runs"
    / "yolov8s_pothole_baseline"
    / "weights"
    / "best.pt"
)

INPUT_DIR = (
    PROJECT_ROOT
    / "module1_road_defect"
    / "data"
    / "processed"
    / "rdd2022_yolo"
    / "images"
    / "test"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "module1_road_defect"
    / "inference"
    / "results"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("YOLOv8s POTHOLE INFERENCE")
    print("=" * 60)

    # --------------------------------------------------------
    # Check GPU
    # --------------------------------------------------------

    print("CUDA:", torch.cuda.is_available())

    if torch.cuda.is_available():
        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

    # --------------------------------------------------------
    # Check model
    # --------------------------------------------------------

    print("\nModel:")
    print(MODEL_PATH)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
        )

    # --------------------------------------------------------
    # Check input directory
    # --------------------------------------------------------

    print("\nInput:")
    print(INPUT_DIR)

    if not INPUT_DIR.exists():
        raise FileNotFoundError(
            f"Input directory not found:\n{INPUT_DIR}"
        )

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    print("\nLoading model...")

    model = YOLO(
        str(MODEL_PATH)
    )

    print("Model loaded successfully.")

    # --------------------------------------------------------
    # Run inference
    # --------------------------------------------------------

    print("\nRunning inference...")

    results = model.predict(
        source=str(INPUT_DIR),
        imgsz=640,
        conf=0.28,
        device=0,
        save=True,
        project=str(OUTPUT_DIR),
        name="baseline_predictions",
        exist_ok=True,
        verbose=True
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("INFERENCE COMPLETE")
    print("=" * 60)

    print(
        "Results saved to:"
    )

    print(
        OUTPUT_DIR
        / "baseline_predictions"
    )


if __name__ == "__main__":
    main()