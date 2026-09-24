from pathlib import Path
import cv2
import random


DATASET_DIR = Path(
    "module1_road_defect/data/processed/rdd2022_yolo"
)

OUTPUT_DIR = Path(
    "module1_road_defect/data/visualization"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

random.seed(42)

# Choose images from the training set
image_dir = DATASET_DIR / "images" / "train"
label_dir = DATASET_DIR / "labels" / "train"

images = list(image_dir.glob("*.jpg"))

# Select 10 random images
selected_images = random.sample(
    images,
    min(10, len(images))
)

for image_path in selected_images:

    label_path = label_dir / f"{image_path.stem}.txt"

    image = cv2.imread(
        str(image_path)
    )

    if image is None:
        print(f"Could not read: {image_path}")
        continue

    height, width = image.shape[:2]

    if label_path.exists():

        lines = label_path.read_text(
            encoding="utf-8"
        ).splitlines()

        for line in lines:

            if not line.strip():
                continue

            parts = line.split()

            if len(parts) != 5:
                continue

            class_id = int(parts[0])

            x_center = float(parts[1])
            y_center = float(parts[2])
            box_width = float(parts[3])
            box_height = float(parts[4])

            # YOLO normalized coordinates → pixels

            x_center *= width
            y_center *= height

            box_width *= width
            box_height *= height

            x1 = int(
                x_center - box_width / 2
            )

            y1 = int(
                y_center - box_height / 2
            )

            x2 = int(
                x_center + box_width / 2
            )

            y2 = int(
                y_center + box_height / 2
            )

            # Draw bounding box
            cv2.rectangle(
                image,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            # Draw class name
            cv2.putText(
                image,
                "pothole",
                (x1, max(y1 - 8, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    output_path = (
        OUTPUT_DIR / image_path.name
    )

    cv2.imwrite(
        str(output_path),
        image
    )

    print(
        f"Saved: {output_path}"
    )


print("\nVisual validation images created.")
print(f"Location: {OUTPUT_DIR.resolve()}")