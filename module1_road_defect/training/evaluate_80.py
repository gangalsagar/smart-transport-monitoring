from pathlib import Path
from ultralytics import YOLO
import torch


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL = (
    PROJECT_ROOT
    / "runs"
    / "module1_road_defect"
    / "yolov8s_extended_80"
    / "weights"
    / "best.pt"
)

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
    print("YOLOv8s EXPERIMENT 3 TEST EVALUATION")
    print("=" * 60)

    # GPU
    print("CUDA:", torch.cuda.is_available())

    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
    else:
        raise RuntimeError("CUDA GPU is not available.")

    # Paths
    print("\nModel path:")
    print(MODEL)
    print("Model exists:", MODEL.exists())

    print("\nDataset path:")
    print(DATASET)
    print("Dataset exists:", DATASET.exists())

    if not MODEL.exists():
        raise FileNotFoundError(
            f"Model not found:\n{MODEL}"
        )

    if not DATASET.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{DATASET}"
        )

    # Load model
    print("\nLoading Experiment 3 model...")

    model = YOLO(str(MODEL))

    print("Model loaded successfully.")

    # Evaluate
    print("\nEvaluating on SAME TEST set...")
    print("Test images: 153")

    results = model.val(
        data=str(DATASET),
        split="test",
        imgsz=640,
        batch=8,
        device=0,
        workers=0,
        plots=True
    )

    # Results
    print("\n" + "=" * 60)
    print("EXPERIMENT 3 TEST RESULTS")
    print("=" * 60)

    print(f"Precision : {results.box.mp:.4f}")
    print(f"Recall    : {results.box.mr:.4f}")
    print(f"mAP@50    : {results.box.map50:.4f}")
    print(f"mAP@50-95 : {results.box.map:.4f}")

    print("\nEvaluation complete.")


if __name__ == "__main__":
    main()