from pathlib import Path
import xml.etree.ElementTree as ET
import random
import shutil


# ============================================================
# CONFIGURATION
# ============================================================

RAW_IMAGES = Path(
    "module1_road_defect/data/raw/train/images"
)

RAW_ANNOTATIONS = Path(
    "module1_road_defect/data/raw/train/annotations/xmls"
)

OUTPUT_DIR = Path(
    "module1_road_defect/data/processed/rdd2022_yolo"
)

# Dataset split
TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10

RANDOM_SEED = 42

# RDD2022 pothole class
TARGET_CLASS = "D40"

# YOLO class ID
YOLO_CLASS_ID = 0


# ============================================================
# CREATE OUTPUT DIRECTORIES
# ============================================================

for split in ["train", "val", "test"]:
    (OUTPUT_DIR / "images" / split).mkdir(
        parents=True,
        exist_ok=True
    )

    (OUTPUT_DIR / "labels" / split).mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# FIND IMAGES
# ============================================================

images = sorted(
    RAW_IMAGES.glob("*.jpg")
)

print(f"Images found: {len(images)}")


# ============================================================
# SHUFFLE DATASET
# ============================================================

random.seed(RANDOM_SEED)

random.shuffle(images)


# ============================================================
# SPLIT DATASET
# ============================================================

total = len(images)

train_end = int(total * TRAIN_RATIO)
val_end = train_end + int(total * VAL_RATIO)

train_images = images[:train_end]
val_images = images[train_end:val_end]
test_images = images[val_end:]


print("\nDataset split:")
print(f"Train: {len(train_images)}")
print(f"Val  : {len(val_images)}")
print(f"Test : {len(test_images)}")


# ============================================================
# VOC → YOLO CONVERSION
# ============================================================

def convert_box(
    xmin,
    ymin,
    xmax,
    ymax,
    image_width,
    image_height
):
    """
    Convert Pascal VOC bounding box
    to normalized YOLO format.
    """

    box_width = xmax - xmin
    box_height = ymax - ymin

    center_x = xmin + (box_width / 2)
    center_y = ymin + (box_height / 2)

    center_x /= image_width
    center_y /= image_height

    box_width /= image_width
    box_height /= image_height

    return (
        center_x,
        center_y,
        box_width,
        box_height
    )


# ============================================================
# PROCESS ONE IMAGE
# ============================================================

def process_image(image_path, split):

    xml_path = RAW_ANNOTATIONS / (
        image_path.stem + ".xml"
    )

    if not xml_path.exists():
        raise FileNotFoundError(
            f"Annotation missing for {image_path.name}"
        )

    tree = ET.parse(xml_path)
    root = tree.getroot()

    size = root.find("size")

    image_width = int(
        size.findtext("width")
    )

    image_height = int(
        size.findtext("height")
    )

    yolo_labels = []

    for obj in root.findall("object"):

        class_name = obj.findtext("name")

        # Keep ONLY D40
        if class_name != TARGET_CLASS:
            continue

        bbox = obj.find("bndbox")

        xmin = float(
            bbox.findtext("xmin")
        )

        ymin = float(
            bbox.findtext("ymin")
        )

        xmax = float(
            bbox.findtext("xmax")
        )

        ymax = float(
            bbox.findtext("ymax")
        )

        (
            center_x,
            center_y,
            width,
            height
        ) = convert_box(
            xmin,
            ymin,
            xmax,
            ymax,
            image_width,
            image_height
        )

        yolo_labels.append(
            f"{YOLO_CLASS_ID} "
            f"{center_x:.6f} "
            f"{center_y:.6f} "
            f"{width:.6f} "
            f"{height:.6f}"
        )

    # --------------------------------------------------------
    # Copy image
    # --------------------------------------------------------

    destination_image = (
        OUTPUT_DIR
        / "images"
        / split
        / image_path.name
    )

    shutil.copy2(
        image_path,
        destination_image
    )

    # --------------------------------------------------------
    # Write YOLO label
    # --------------------------------------------------------

    destination_label = (
        OUTPUT_DIR
        / "labels"
        / split
        / f"{image_path.stem}.txt"
    )

    destination_label.write_text(
        "\n".join(yolo_labels),
        encoding="utf-8"
    )

    return len(yolo_labels)


# ============================================================
# PROCESS DATASET
# ============================================================

total_d40_boxes = 0

for split, split_images in [
    ("train", train_images),
    ("val", val_images),
    ("test", test_images)
]:

    print(f"\nProcessing {split}...")

    for image_path in split_images:

        boxes = process_image(
            image_path,
            split
        )

        total_d40_boxes += boxes


# ============================================================
# CREATE data.yaml
# ============================================================

yaml_content = f"""path: {OUTPUT_DIR.resolve()}
train: images/train
val: images/val
test: images/test

names:
  0: pothole
"""

yaml_path = OUTPUT_DIR / "data.yaml"

yaml_path.write_text(
    yaml_content,
    encoding="utf-8"
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n==========================================")
print("RDD2022 → YOLO CONVERSION COMPLETE")
print("==========================================")

print(f"Total images      : {total}")
print(f"Training images   : {len(train_images)}")
print(f"Validation images : {len(val_images)}")
print(f"Test images       : {len(test_images)}")
print(f"D40 boxes         : {total_d40_boxes}")

print(f"\nOutput:")
print(OUTPUT_DIR.resolve())

print("\ndata.yaml created successfully.")