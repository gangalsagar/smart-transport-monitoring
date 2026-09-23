from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
from ultralytics import YOLO

from shared.config import Config


class VehicleDetector:
    """
    Reusable Indian vehicle detector using Ultralytics YOLO.

    Features:
    - Filters only configured vehicle classes.
    - Uses class-specific confidence thresholds.
    - Reduces false motorbike detections.
    - Normalizes rickshaw / three-wheeler labels into auto rickshaw.
    """

    # ------------------------------------------------------------
    # CLASS NORMALIZATION
    # ------------------------------------------------------------
    CLASS_ALIASES = {
        "rickshaw": "auto rickshaw",
        "three wheelers -cng-": "auto rickshaw",
        "three wheelers -CNG-": "auto rickshaw",
        "auto-rickshaw": "auto rickshaw",
        "autorickshaw": "auto rickshaw",
        "motorcycle": "motorbike",
    }

    # ------------------------------------------------------------
    # CLASS-SPECIFIC CONFIDENCE THRESHOLDS
    #
    # Motorbike is intentionally higher because your model is
    # incorrectly detecting some humans as motorbikes.
    # ------------------------------------------------------------
    CLASS_CONFIDENCE_THRESHOLDS = {
        "ambulance": 0.40,
        "army vehicle": 0.40,
        "auto rickshaw": 0.35,
        "bicycle": 0.40,
        "bus": 0.35,
        "car": 0.35,
        "garbagevan": 0.40,
        "human hauler": 0.45,
        "minibus": 0.40,
        "minivan": 0.40,
        "motorbike": 0.65,
        "pickup": 0.40,
        "policecar": 0.40,
        "rickshaw": 0.40,
        "scooter": 0.45,
        "suv": 0.45,
        "taxi": 0.40,
        "three wheelers -cng-": 0.40,
        "truck": 0.35,
        "van": 0.40,
        "wheelbarrow": 0.50,
    }

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        confidence: Optional[float] = None,
        image_size: Optional[int] = None,
        device: Optional[Any] = None,
        allowed_classes: Optional[List[str]] = None,
    ):

        config = Config()

        # --------------------------------------------------------
        # MODEL PATH
        # --------------------------------------------------------
        if model_path is None:
            model_path = config.resolve_path(
                config.traffic_model_path
            )
        else:
            model_path = Path(model_path)

        self.model_path = model_path

        # --------------------------------------------------------
        # GENERAL CONFIDENCE
        # --------------------------------------------------------
        self.confidence = float(
            confidence
            if confidence is not None
            else config.traffic_confidence
        )

        # --------------------------------------------------------
        # IMAGE SIZE
        # --------------------------------------------------------
        self.image_size = int(
            image_size
            if image_size is not None
            else config.traffic_image_size
        )

        # --------------------------------------------------------
        # DEVICE
        # --------------------------------------------------------
        self.device = (
            device
            if device is not None
            else config.traffic_inference_device
        )

        # --------------------------------------------------------
        # ALLOWED CLASSES
        # --------------------------------------------------------
        self.allowed_classes = (
            allowed_classes
            if allowed_classes is not None
            else config.traffic_classes
        )

        # Normalize configured classes.
        self.allowed_classes = [
            self.normalize_class_name(class_name)
            for class_name in self.allowed_classes
        ]

        # Remove duplicates.
        self.allowed_classes = list(
            dict.fromkeys(self.allowed_classes)
        )

        # --------------------------------------------------------
        # CHECK MODEL
        # --------------------------------------------------------
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"YOLO vehicle model not found:\n"
                f"{self.model_path}"
            )

        # --------------------------------------------------------
        # LOAD MODEL
        # --------------------------------------------------------
        self.model = YOLO(str(self.model_path))

        # --------------------------------------------------------
        # MAP MODEL CLASS IDs
        #
        # Example:
        #
        # model:
        #   2 -> auto rickshaw
        #   13 -> rickshaw
        #   17 -> three wheelers -CNG-
        #
        # all three become:
        #
        #   auto rickshaw
        # --------------------------------------------------------
        self.target_class_ids: Dict[int, str] = {}

        for class_id, name in self.model.names.items():

            original_name = str(name).strip().lower()

            normalized_name = self.normalize_class_name(
                original_name
            )

            if normalized_name in self.allowed_classes:

                self.target_class_ids[
                    class_id
                ] = normalized_name

        if not self.target_class_ids:
            raise RuntimeError(
                "No configured traffic classes were found "
                "in the YOLO model.\n\n"
                f"Configured classes: {self.allowed_classes}\n"
                f"Model classes: {self.model.names}"
            )

    # ============================================================
    # CLASS NORMALIZATION
    # ============================================================

    @classmethod
    def normalize_class_name(
        cls,
        class_name: str,
    ) -> str:
        """
        Convert different model labels representing the same
        vehicle type into one canonical class name.
        """

        normalized = str(class_name).strip().lower()

        return cls.CLASS_ALIASES.get(
            normalized,
            normalized,
        )

    # ============================================================
    # CLASS CONFIDENCE
    # ============================================================

    def get_class_confidence_threshold(
        self,
        class_name: str,
    ) -> float:
        """
        Return confidence threshold for a specific vehicle class.

        Falls back to the global configured confidence.
        """

        normalized_name = self.normalize_class_name(
            class_name
        )

        return float(
            self.CLASS_CONFIDENCE_THRESHOLDS.get(
                normalized_name,
                self.confidence,
            )
        )

    # ============================================================
    # DETECTION
    # ============================================================

    def detect(
        self,
        image: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """
        Run inference and return filtered vehicle detections.

        Returns:

        [
            {
                "class_id": int,
                "class_name": str,
                "confidence": float,
                "bbox": {
                    "xmin": float,
                    "ymin": float,
                    "xmax": float,
                    "ymax": float
                }
            }
        ]
        """

        # --------------------------------------------------------
        # RUN YOLO
        #
        # Use a lower initial confidence so class-specific filtering
        # below controls which detections are finally accepted.
        # --------------------------------------------------------
        inference_confidence = min(
            self.confidence,
            0.25,
        )

        results = self.model.predict(
            source=image,
            imgsz=self.image_size,
            conf=inference_confidence,
            device=self.device,
            verbose=False,
        )

        detections: List[Dict[str, Any]] = []

        # --------------------------------------------------------
        # PROCESS RESULTS
        # --------------------------------------------------------
        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                # ------------------------------------------------
                # CLASS ID
                # ------------------------------------------------
                class_id = int(
                    box.cls[0].cpu().item()
                )

                # Ignore classes not configured.
                if class_id not in self.target_class_ids:
                    continue

                # ------------------------------------------------
                # NORMALIZED CLASS NAME
                # ------------------------------------------------
                class_name = (
                    self.target_class_ids[class_id]
                )

                # ------------------------------------------------
                # DETECTION CONFIDENCE
                # ------------------------------------------------
                detection_confidence = float(
                    box.conf[0].cpu().item()
                )

                # ------------------------------------------------
                # CLASS-SPECIFIC CONFIDENCE FILTER
                #
                # Example:
                #
                # A motorbike detected at confidence 0.53
                # will now be rejected because motorbike requires
                # confidence >= 0.65.
                # ------------------------------------------------
                minimum_confidence = (
                    self.get_class_confidence_threshold(
                        class_name
                    )
                )

                if (
                    detection_confidence
                    < minimum_confidence
                ):
                    continue

                # ------------------------------------------------
                # BOUNDING BOX
                # ------------------------------------------------
                xyxy = (
                    box.xyxy[0]
                    .cpu()
                    .numpy()
                    .tolist()
                )

                xmin = float(xyxy[0])
                ymin = float(xyxy[1])
                xmax = float(xyxy[2])
                ymax = float(xyxy[3])

                # ------------------------------------------------
                # BASIC BOX VALIDATION
                # ------------------------------------------------
                width = xmax - xmin
                height = ymax - ymin

                if width <= 0 or height <= 0:
                    continue

                # ------------------------------------------------
                # EXTRA MOTORBIKE FALSE-POSITIVE FILTER
                #
                # Extremely tall and narrow boxes are more likely
                # to be standing people than motor vehicles.
                # ------------------------------------------------
                if class_name == "motorbike":

                    aspect_ratio = height / max(
                        width,
                        1.0,
                    )

                    # Reject extremely tall/narrow detections.
                    if aspect_ratio > 3.5:
                        continue

                # ------------------------------------------------
                # SAVE DETECTION
                # ------------------------------------------------
                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": detection_confidence,
                        "bbox": {
                            "xmin": xmin,
                            "ymin": ymin,
                            "xmax": xmax,
                            "ymax": ymax,
                        },
                    }
                )

        return detections


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 60)
    print("VEHICLE DETECTOR TEST")
    print("=" * 60)

    detector = VehicleDetector()

    print(
        f"Model path      : "
        f"{detector.model_path}"
    )

    print(
        f"Confidence      : "
        f"{detector.confidence}"
    )

    print(
        f"Image size      : "
        f"{detector.image_size}"
    )

    print(
        f"Device          : "
        f"{detector.device}"
    )

    print(
        f"Allowed classes : "
        f"{list(set(detector.target_class_ids.values()))}"
    )

    print()
    print(
        "Class confidence thresholds:"
    )

    for class_name in sorted(
        set(detector.target_class_ids.values())
    ):
        print(
            f"  {class_name}: "
            f"{detector.get_class_confidence_threshold(class_name)}"
        )

    print()
    print(
        "VehicleDetector initialized successfully."
    )


if __name__ == "__main__":
    main()