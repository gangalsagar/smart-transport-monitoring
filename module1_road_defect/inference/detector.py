from pathlib import Path

from ultralytics import YOLO

from shared.config import Config


class RoadDefectDetector:
    """
    Reusable road-defect detector.

    Configuration is loaded from config/config.yaml.

    The detector remains independent of:
        - camera source
        - GPS provider
        - backend
        - alert queue

    This makes it suitable for:
        - development PC
        - mobile edge demonstration
        - future dedicated edge hardware
    """

    def __init__(
        self,
        model_path=None,
        confidence=None,
        image_size=None,
        device=None,
    ):

        config = Config()

        project_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        # ----------------------------------------------------
        # MODEL
        # ----------------------------------------------------

        if model_path is None:

            model_path = (
                project_root
                / config.model_path
            )

        self.model_path = Path(
            model_path
        )

        # ----------------------------------------------------
        # INFERENCE SETTINGS
        # ----------------------------------------------------

        if confidence is None:
            confidence = config.confidence

        if image_size is None:
            image_size = config.image_size

        if device is None:
            device = config.inference_device

        self.confidence = float(
            confidence
        )

        self.image_size = int(
            image_size
        )

        self.device = device

        # ----------------------------------------------------
        # VALIDATE MODEL
        # ----------------------------------------------------

        if not self.model_path.exists():

            raise FileNotFoundError(
                f"Model not found:\n"
                f"{self.model_path}"
            )

        # ----------------------------------------------------
        # LOAD YOLO MODEL
        # ----------------------------------------------------

        self.model = YOLO(
            str(self.model_path)
        )

    # ========================================================
    # DETECTION
    # ========================================================

    def detect(self, image):

        results = self.model.predict(
            source=image,
            imgsz=self.image_size,
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )

        detections = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                xyxy = (
                    box.xyxy[0]
                    .cpu()
                    .numpy()
                    .tolist()
                )

                confidence = float(
                    box.conf[0]
                    .cpu()
                    .item()
                )

                class_id = int(
                    box.cls[0]
                    .cpu()
                    .item()
                )

                detections.append(
                    {
                        "class_id": class_id,

                        "class_name": "pothole",

                        "confidence": confidence,

                        "bbox": {
                            "xmin": xyxy[0],
                            "ymin": xyxy[1],
                            "xmax": xyxy[2],
                            "ymax": xyxy[3],
                        },
                    }
                )

        return detections


def main():

    print("=" * 60)
    print("ROAD DEFECT DETECTOR CONFIGURATION TEST")
    print("=" * 60)

    detector = RoadDefectDetector()

    print(
        f"\nModel:"
        f"\n{detector.model_path}"
    )

    print(
        f"\nConfidence:"
        f"\n{detector.confidence}"
    )

    print(
        f"\nImage size:"
        f"\n{detector.image_size}"
    )

    print(
        f"\nDevice:"
        f"\n{detector.device}"
    )

    print(
        "\nDetector configuration test passed."
    )


if __name__ == "__main__":
    main()