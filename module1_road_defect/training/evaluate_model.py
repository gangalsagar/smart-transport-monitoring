from pathlib import Path
from ultralytics import YOLO
import torch


# ============================================================
# PROJECT PATHS
# ============================================================

# Project root:
# C:\SIH\prototype\smart-transport-monitoring

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# Trained YOLOv8s model
MODEL = (
    PROJECT_ROOT
    / "runs"
    / "detect"
    / "module1_road_defect"
    / "runs"
    / "yolov8s_pothole_baseline"
    / "weights"
    / "best.pt"
)


# YOLO dataset configuration
DATASET = (
    PROJECT_ROOT
    / "module1_road_defect"
    / "data"
    / "processed"
    / "rdd2022_yolo"
    / "data.yaml"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("YOLOv8s TEST EVALUATION")
    print("=" * 60)

    # --------------------------------------------------------
    # Check CUDA
    # --------------------------------------------------------

    print("CUDA:", torch.cuda.is_available())

    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
    else:
        raise RuntimeError(
            "CUDA GPU is not available."
        )

    # --------------------------------------------------------
    # Check paths
    # --------------------------------------------------------

    print("\nModel path:")
    print(MODEL)

    print("\nModel exists:", MODEL.exists())

    print("\nDataset path:")
    print(DATASET)

    print("Dataset exists:", DATASET.exists())

    if not MODEL.exists():
        raise FileNotFoundError(
            f"\nModel file not found:\n{MODEL}"
        )

    if not DATASET.exists():
        raise FileNotFoundError(
            f"\nDataset YAML not found:\n{DATASET}"
        )

    # --------------------------------------------------------
    # Load trained model
    # --------------------------------------------------------

    print("\nLoading trained YOLOv8s model...")

    model = YOLO(str(MODEL))

    print("Model loaded successfully.")

    # --------------------------------------------------------
    # Evaluate on TEST set
    # --------------------------------------------------------

    print("\nEvaluating on TEST set...")

    results = model.val(
        data=str(DATASET),
        split="test",
        imgsz=640,
        batch=8,
        device=0,
        workers=0,
        plots=True
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    print(f"Precision : {results.box.mp:.4f}")
    print(f"Recall    : {results.box.mr:.4f}")
    print(f"mAP@50    : {results.box.map50:.4f}")
    print(f"mAP@50-95 : {results.box.map:.4f}")

    print("\nEvaluation complete.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()