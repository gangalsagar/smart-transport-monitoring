from ultralytics import YOLO
import torch


DATASET = (
    "module1_road_defect/data/processed/"
    "rdd2022_yolo/data.yaml"
)


print("=" * 50)
print("YOLOv8s GPU SMOKE TEST")
print("=" * 50)

print("PyTorch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("CUDA available:", torch.cuda.is_available())

if not torch.cuda.is_available():
    raise RuntimeError("CUDA is not available.")

print("GPU:", torch.cuda.get_device_name(0))

print("\nLoading YOLOv8s...")

model = YOLO("yolov8s.pt")

print("Model loaded successfully.")

print("\nStarting 2-epoch smoke test...")

results = model.train(
    data=DATASET,

    epochs=2,
    imgsz=640,
    batch=4,

    device=0,

    workers=0,

    project="module1_road_defect/runs",
    name="yolov8s_smoke_test",

    seed=42,

    save=True,

    # Basic augmentation
    degrees=5.0,
    translate=0.1,
    scale=0.5,
    fliplr=0.5,
    mosaic=1.0,

    patience=2,
)

print("\n" + "=" * 50)
print("SMOKE TEST COMPLETE")
print("=" * 50)

print("Training completed successfully.")