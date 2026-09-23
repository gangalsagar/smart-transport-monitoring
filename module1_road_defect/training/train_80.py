from pathlib import Path
from ultralytics import YOLO
import torch


# ============================================================
# PROJECT PATHS
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
    / "last.pt"
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
    print("YOLOv8s EXPERIMENT 3 - EXTENDED TRAINING")
    print("=" * 60)

    # --------------------------------------------------------
    # GPU check
    # --------------------------------------------------------

    print("PyTorch:", torch.__version__)
    print("CUDA:", torch.version.cuda)
    print("CUDA available:", torch.cuda.is_available())

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is not available.")

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    print("\nStarting checkpoint:")
    print(MODEL_PATH)

    print("Checkpoint exists:", MODEL_PATH.exists())

    print("\nDataset:")
    print(DATASET)

    print("Dataset exists:", DATASET.exists())

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"last.pt not found:\n{MODEL_PATH}"
        )

    if not DATASET.exists():
        raise FileNotFoundError(
            f"data.yaml not found:\n{DATASET}"
        )

    # --------------------------------------------------------
    # Load the epoch-50 checkpoint
    # --------------------------------------------------------

    print("\nLoading epoch-50 checkpoint...")

    model = YOLO(str(MODEL_PATH))

    print("Checkpoint loaded successfully.")

    # --------------------------------------------------------
    # Continue training
    # --------------------------------------------------------

    print("\nStarting Experiment 3...")
    print("Starting checkpoint: epoch 50")
    print("Additional epochs: 30")
    print("Resolution: 640x640")
    print("Batch: 8")
    print("Device: GPU")
    print("Workers: 0")

    model.train(
        data=str(DATASET),

        # Same winning configuration
        imgsz=640,
        batch=8,

        # 30 additional epochs
        epochs=30,

        # GPU
        device=0,
        workers=0,

        # Reproducibility
        seed=42,
        deterministic=True,

        # Output to a NEW experiment directory
        project=str(
            PROJECT_ROOT
            / "runs"
            / "module1_road_defect"
        ),
        name="yolov8s_extended_80",

        # Validation
        val=True,

        # Save
        save=True,
        save_period=10,

        # Augmentation
        degrees=5.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,

        # Mixed precision
        amp=True,

        # Early stopping
        patience=10,

        verbose=True
    )

    print("\n" + "=" * 60)
    print("EXPERIMENT 3 TRAINING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()