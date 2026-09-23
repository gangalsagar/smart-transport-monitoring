from ultralytics import YOLO
import torch


DATASET = (
    "module1_road_defect/data/processed/"
    "rdd2022_yolo/data.yaml"
)


def main():

    print("=" * 60)
    print("YOLOv8s POTHOLE DETECTION - FULL TRAINING")
    print("=" * 60)

    print("PyTorch:", torch.__version__)
    print("CUDA:", torch.version.cuda)
    print("CUDA available:", torch.cuda.is_available())

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU not available.")

    print("GPU:", torch.cuda.get_device_name(0))

    # --------------------------------------------------------
    # Load pretrained YOLOv8s
    # --------------------------------------------------------

    model = YOLO("yolov8s.pt")

    # --------------------------------------------------------
    # Full baseline training
    # --------------------------------------------------------

    model.train(
        data=DATASET,

        # Training
        epochs=50,
        imgsz=640,
        batch=8,

        # GPU
        device=0,

        # Windows stability
        workers=0,

        # Reproducibility
        seed=42,

        # Early stopping
        patience=10,

        # Save checkpoints
        save=True,
        save_period=10,

        # Output
        project="module1_road_defect/runs",
        name="yolov8s_pothole_baseline",

        # Augmentation
        degrees=5.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,

        # Validation
        val=True,

        # Mixed precision
        amp=True,
    )

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()