from pathlib import Path

import cv2

from module1_road_defect.inference.detector import (
    RoadDefectDetector
)

from module1_road_defect.inference.evidence import (
    EvidenceGenerator
)

from module1_road_defect.telemetry.gps import (
    SimulatedGPSProvider
)

from shared.schemas.alert_schema import (
    Alert,
    Evidence
)


def main():

    # ========================================================
    # PROJECT PATHS
    # ========================================================

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

    # ========================================================
    # LOAD IMAGE
    # ========================================================

    image = cv2.imread(
        str(image_path)
    )

    if image is None:
        raise RuntimeError(
            f"Could not read image:\n{image_path}"
        )

    # ========================================================
    # INITIALIZE COMPONENTS
    # ========================================================

    print("=" * 60)
    print("DETECTION → GPS → EVIDENCE → ALERT TEST")
    print("=" * 60)

    print(
        f"\nImage: {image_path.name}"
    )

    detector = RoadDefectDetector()

    evidence_generator = (
        EvidenceGenerator()
    )

    gps_provider = (
        SimulatedGPSProvider()
    )

    # ========================================================
    # GET GPS POSITION
    # ========================================================

    gps_position = (
        gps_provider.get_position()
    )

    print("\nGPS position:")

    print(
        f"  Latitude  : "
        f"{gps_position.latitude}"
    )

    print(
        f"  Longitude : "
        f"{gps_position.longitude}"
    )

    print(
        f"  Accuracy  : "
        f"{gps_position.accuracy_m} m"
    )

    print(
        f"  Timestamp : "
        f"{gps_position.timestamp.isoformat()}"
    )

    # ========================================================
    # YOLO DETECTION
    # ========================================================

    detections = detector.detect(
        image
    )

    print(
        f"\nDetections found: "
        f"{len(detections)}"
    )

    # ========================================================
    # NO DETECTION CASE
    # ========================================================

    if not detections:

        print(
            "\nNo pothole detected."
        )

        print(
            "No alert generated."
        )

        return

    # ========================================================
    # GENERATE EVIDENCE
    # ========================================================

    evidence_path = (
        evidence_generator.generate(
            image=image,
            detections=detections,
            image_name=image_path.name
        )
    )

    print(
        "\nEvidence generated:"
    )

    print(
        evidence_path
    )

    # ========================================================
    # CREATE EVIDENCE OBJECT
    # ========================================================

    evidence = Evidence(
        image_path=str(
            evidence_path
        )
    )

    # ========================================================
    # CREATE ALERTS
    # ========================================================

    alerts = []

    for index, detection in enumerate(
        detections,
        start=1
    ):

        confidence = (
            detection["confidence"]
        )

        # ----------------------------------------------------
        # Prototype severity rule
        # ----------------------------------------------------

        if confidence >= 0.70:
            severity = "high"

        elif confidence >= 0.45:
            severity = "medium"

        else:
            severity = "low"

        bbox = detection["bbox"]

        # ----------------------------------------------------
        # Create alert
        # ----------------------------------------------------

        alert = Alert(

            alert_id=f"ALT-{index:04d}",

            bus_id="BUS-TEST",

            # Use GPS timestamp
            timestamp=gps_position.timestamp,

            # Use GPS provider
            gps={
                "latitude": gps_position.latitude,
                "longitude": gps_position.longitude,
                "accuracy_m": gps_position.accuracy_m,
            },

            module={
                "type": "road_defect",
                "version": "1.0",
            },

            severity=severity,

            payload={
                "defect_type": "pothole",
                "confidence": confidence,
                "bounding_box": bbox,
                "image": image_path.name,
            },

            source={
                "device_id": "EDGE-01",
                "camera_id": "FRONT_CAM",
            },

            evidence=evidence,
        )

        alerts.append(alert)

    # ========================================================
    # PRINT ALERTS
    # ========================================================

    print(
        f"\nAlerts generated: "
        f"{len(alerts)}"
    )

    for alert in alerts:

        print(
            "\n" + "-" * 60
        )

        print(
            alert.model_dump_json(
                indent=4
            )
        )

    # ========================================================
    # COMPLETE
    # ========================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "DETECTION → GPS → EVIDENCE → ALERT "
        "TEST COMPLETE"
    )

    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()