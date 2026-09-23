from pathlib import Path
import cv2

from detector import RoadDefectDetector


def main():

    project_root = Path(__file__).resolve().parents[2]

    image_dir = (
        project_root
        / "module1_road_defect"
        / "data"
        / "processed"
        / "rdd2022_yolo"
        / "images"
        / "test"
    )

    images = list(
        image_dir.glob("*.jpg")
    )

    if not images:
        raise RuntimeError(
            f"No test images found:\n{image_dir}"
        )

    image_path = images[0]

    print("=" * 60)
    print("ROAD DEFECT DETECTOR TEST")
    print("=" * 60)

    print("Image:")
    print(image_path)

    image = cv2.imread(
        str(image_path)
    )

    if image is None:
        raise RuntimeError(
            "Could not read image."
        )

    detector = RoadDefectDetector()

    detections = detector.detect(
        image
    )

    print(
        f"\nDetections found: {len(detections)}"
    )

    for i, detection in enumerate(
        detections,
        start=1
    ):

        print(
            f"\nDetection {i}"
        )

        print(
            f"  Class      : "
            f"{detection['class_name']}"
        )

        print(
            f"  Confidence : "
            f"{detection['confidence']:.4f}"
        )

        print(
            f"  Bounding box: "
            f"{detection['bbox']}"
        )

    print("\nDetector test complete.")


if __name__ == "__main__":
    main()