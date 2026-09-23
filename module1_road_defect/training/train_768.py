from pathlib import Path
from ultralytics import YOLO
import torch


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
    print("YOLOv8s EXPERIMENT 2 - 768x768")
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
    # Dataset check
    # --------------------------------------------------------

    print("\nDataset:")
    print(DATASET)

    if not DATASET.exists():
        raise FileNotFoundError(
            f"Dataset YAML not found:\n{DATASET}"
        )

    print("Dataset exists: True")

    # --------------------------------------------------------
    # Load pretrained YOLOv8s
    # --------------------------------------------------------

    print("\nLoading YOLOv8s pretrained model...")

    model = YOLO("yolov8s.pt")

    print("Model loaded successfully.")

    # --------------------------------------------------------
    # Training
    # --------------------------------------------------------

    print("\nStarting Experiment 2...")
    print("Resolution: 768x768")
    print("Epochs: 50")
    print("Batch: 4")
    print("Device: GPU")

    results = model.train(
        data=str(DATASET),

        # Main experiment change
        imgsz=768,

        # Training
        epochs=50,
        batch=4,

        # GPU
        device=0,
        workers=0,

        # Reproducibility
        seed=42,
        deterministic=True,

        # Pretrained model
        pretrained=True,

        # Save results separately
        project=str(
            PROJECT_ROOT
            / "runs"
            / "module1_road_defect"
        ),
        name="yolov8s_768_experiment",

        # Validation
        val=True,

        # Save best model
        save=True,

        # Standard YOLO augmentation
        augment=True,

        verbose=True
    )

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("EXPERIMENT 2 TRAINING COMPLETE")
    print("=" * 60)

    print(
        "Results saved to:"
    )

    print(
        PROJECT_ROOT
        / "runs"
        / "module1_road_defect"
        / "yolov8s_768_experiment"
    )


if __name__ == "__main__":
    main()