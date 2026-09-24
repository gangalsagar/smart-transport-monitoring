from pathlib import Path


DATASET_DIR = Path(
    "module1_road_defect/data/processed/rdd2022_yolo"
)


errors = []

total_images = 0
total_labels = 0
total_boxes = 0


for split in ["train", "val", "test"]:

    image_dir = DATASET_DIR / "images" / split
    label_dir = DATASET_DIR / "labels" / split

    images = list(image_dir.glob("*.jpg"))
    labels = list(label_dir.glob("*.txt"))

    print(f"\n========== {split.upper()} ==========")

    print(f"Images : {len(images)}")
    print(f"Labels : {len(labels)}")

    total_images += len(images)
    total_labels += len(labels)

    image_stems = {
        image.stem
        for image in images
    }

    label_stems = {
        label.stem
        for label in labels
    }

    # --------------------------------------------------------
    # Check image/label correspondence
    # --------------------------------------------------------

    missing_labels = image_stems - label_stems
    missing_images = label_stems - image_stems

    if missing_labels:
        errors.append(
            f"{split}: Missing labels: {len(missing_labels)}"
        )

    if missing_images:
        errors.append(
            f"{split}: Missing images: {len(missing_images)}"
        )

    # --------------------------------------------------------
    # Validate every label
    # --------------------------------------------------------

    for label_file in labels:

        lines = label_file.read_text(
            encoding="utf-8"
        ).splitlines()

        for line_number, line in enumerate(
            lines,
            start=1
        ):

            if not line.strip():
                continue

            parts = line.split()

            # Must be:
            # class x_center y_center width height

            if len(parts) != 5:

                errors.append(
                    f"{label_file.name}: "
                    f"Line {line_number} does not contain 5 values"
                )

                continue

            try:

                class_id = int(parts[0])

                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])

            except ValueError:

                errors.append(
                    f"{label_file.name}: "
                    f"Invalid numeric value"
                )

                continue

            # ------------------------------------------------
            # Class check
            # ------------------------------------------------

            if class_id != 0:

                errors.append(
                    f"{label_file.name}: "
                    f"Invalid class ID {class_id}"
                )

            # ------------------------------------------------
            # Coordinate checks
            # ------------------------------------------------

            values = [
                x_center,
                y_center,
                width,
                height
            ]

            if not all(
                0 <= value <= 1
                for value in values
            ):

                errors.append(
                    f"{label_file.name}: "
                    f"Coordinate outside [0,1]"
                )

            if width <= 0 or height <= 0:

                errors.append(
                    f"{label_file.name}: "
                    f"Width/height must be positive"
                )

            total_boxes += 1

        total_labels += 0


# ============================================================
# FINAL RESULTS
# ============================================================

print("\n==========================================")
print("YOLO DATASET VALIDATION")
print("==========================================")

print(f"Total images : {total_images}")
print(f"Total labels : {total_labels}")
print(f"Total boxes  : {total_boxes}")

print("\nExpected boxes: 3187")

if total_boxes == 3187:
    print("Box count: PASS")
else:
    print(
        f"Box count: FAIL "
        f"(found {total_boxes})"
    )


if errors:

    print("\nVALIDATION ERRORS:")

    for error in errors[:20]:
        print(f"  - {error}")

    if len(errors) > 20:
        print(
            f"\n...and {len(errors) - 20} more errors."
        )

else:

    print("\nAll validation checks PASSED.")