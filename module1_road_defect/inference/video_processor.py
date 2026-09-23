from pathlib import Path
import uuid

import cv2

from module1_road_defect.inference.detector import RoadDefectDetector
from module1_road_defect.inference.evidence import EvidenceGenerator
from module1_road_defect.inference.pothole_tracker import PotholeTracker
from module1_road_defect.inference.alert_store import AlertStore

from module1_road_defect.telemetry.gps import (
    GPSProvider,
    SimulatedGPSProvider,
)

from shared.config import Config
from shared.schemas.alert_schema import Alert, Evidence


class VideoProcessor:
    """
    Edge AI road-defect vision pipeline.

    Pipeline:

        Video / Camera
            ↓
        YOLO detection
            ↓
        Pothole tracking
            ↓
        GPS provider
            ↓
        Evidence generation
            ↓
        Alert creation
            ↓
        Local alert persistence
            ↓
        Edge queue / synchronization

    IMPORTANT:

    This class does NOT communicate directly with the
    central backend.

    Backend delivery is handled separately by:

        AlertQueue
            ↓
        AlertSync

    GPS is provider-based.

    The same vision pipeline can therefore work with:

        - simulated GPS
        - mobile phone GPS
        - dedicated GNSS hardware

    without changing the detection pipeline.
    """

    def __init__(
        self,
        video_path=None,
        output_video_path=None,
        frame_skip=None,
        confidence=None,
        backend_url=None,
        gps_provider=None,
        bus_id=None,
        device_id=None,
        camera_id=None,
    ):

        # ====================================================
        # CENTRAL CONFIGURATION
        # ====================================================

        self.config = Config()

        project_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        # ====================================================
        # INPUT VIDEO
        # ====================================================

        if video_path is None:

            video_path = (
                project_root
                / self.config.input_video
            )

        self.video_path = Path(
            video_path
        )

        # ====================================================
        # OUTPUT VIDEO
        # ====================================================

        if output_video_path is None:

            output_video_path = (
                project_root
                / self.config.output_video
            )

        self.output_video_path = Path(
            output_video_path
        )

        self.output_video_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ====================================================
        # VISION CONFIGURATION
        # ====================================================

        if frame_skip is None:

            frame_skip = (
                self.config.frame_skip
            )

        if confidence is None:

            confidence = (
                self.config.confidence
            )

        self.frame_skip = int(
            frame_skip
        )

        self.confidence = float(
            confidence
        )

        # ====================================================
        # BACKEND CONFIGURATION
        #
        # Kept here for compatibility and diagnostics.
        #
        # This processor NEVER sends alerts directly.
        # ====================================================

        if backend_url is None:

            backend_url = (
                self.config.backend_url
            )

        self.backend_url = (
            backend_url.rstrip("/")
            if backend_url
            else None
        )

        # ====================================================
        # EDGE DEVICE IDENTITY
        # ====================================================

        if bus_id is None:

            bus_id = (
                self.config.bus_id
            )

        if device_id is None:

            device_id = (
                self.config.device_id
            )

        if camera_id is None:

            camera_id = (
                self.config.camera_id
            )

        self.bus_id = bus_id
        self.device_id = device_id
        self.camera_id = camera_id

        # ====================================================
        # YOLO DETECTOR
        #
        # Detector reads model/image/device configuration
        # from Config.
        # ====================================================

        self.detector = RoadDefectDetector(
            confidence=self.confidence
        )

        # ====================================================
        # GPS PROVIDER
        #
        # Explicit provider injection has priority.
        #
        # This allows:
        #
        #   development -> simulated
        #   phone demo   -> phone
        #   production   -> GNSS
        #
        # The vision pipeline remains unchanged.
        # ====================================================

        if gps_provider is None:

            gps_provider = (
                SimulatedGPSProvider()
            )

        if not isinstance(
            gps_provider,
            GPSProvider,
        ):

            raise TypeError(
                "gps_provider must be "
                "a GPSProvider instance."
            )

        self.gps_provider = gps_provider

        # ====================================================
        # EVIDENCE GENERATOR
        # ====================================================

        self.evidence_generator = (
            EvidenceGenerator()
        )

        # ====================================================
        # POTHOLE TRACKER
        #
        # Tracker reads:
        #
        #   IoU threshold
        #   confirmation hits
        #   maximum missing frames
        #
        # from Config.
        # ====================================================

        self.tracker = PotholeTracker()

        # ====================================================
        # LOCAL ALERT STORAGE
        # ====================================================

        self.alert_store = AlertStore()

        # ====================================================
        # RUNTIME STATE
        # ====================================================

        self.alerts = []

        self.alerted_tracks = set()

    # ========================================================
    # UNIQUE ALERT ID
    # ========================================================

    def generate_alert_id(self):
        """
        Generate a globally unique alert ID.

        UUID-based IDs prevent collisions across:

            - process restarts
            - video files
            - buses
            - edge devices
        """

        return (
            f"ALT-"
            f"{uuid.uuid4().hex[:12].upper()}"
        )

    # ========================================================
    # PROCESS VIDEO
    # ========================================================

    def process(self):

        if not self.video_path.exists():

            raise FileNotFoundError(
                f"Video not found:\n"
                f"{self.video_path}"
            )

        print("=" * 60)

        print(
            "EDGE ROAD-DEFECT VIDEO PROCESSOR"
        )

        print("=" * 60)

        print(
            f"\nInput video:\n"
            f"{self.video_path}"
        )

        print(
            f"\nOutput video:\n"
            f"{self.output_video_path}"
        )

        print(
            f"\nFrame skip: "
            f"{self.frame_skip}"
        )

        # ====================================================
        # BACKEND
        # ====================================================

        print(
            "\nBackend transmission:"
        )

        print(
            "  DISABLED"
        )

        print(
            "  Alerts are persisted locally."
        )

        print(
            "  AlertSync handles backend delivery."
        )

        # ====================================================
        # GPS
        # ====================================================

        print(
            "\nGPS provider:"
        )

        print(
            f"  {type(self.gps_provider).__name__}"
        )

        # ====================================================
        # TRACKER
        # ====================================================

        print(
            "\nTracker:"
        )

        print(
            f"  IoU threshold : "
            f"{self.tracker.iou_threshold}"
        )

        print(
            f"  Confirmation  : "
            f"{self.tracker.confirmation_hits} hits"
        )

        print(
            f"  Track expiry  : "
            f"{self.tracker.max_missing_frames} frames"
        )

        # ====================================================
        # OPEN VIDEO
        # ====================================================

        capture = cv2.VideoCapture(
            str(self.video_path)
        )

        if not capture.isOpened():

            raise RuntimeError(
                "Could not open video."
            )

        fps = capture.get(
            cv2.CAP_PROP_FPS
        )

        width = int(
            capture.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        height = int(
            capture.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        total_frames = int(
            capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        if fps <= 0:

            fps = 30.0

        print(
            f"\nVideo FPS: "
            f"{fps:.2f}"
        )

        print(
            f"Resolution: "
            f"{width}x{height}"
        )

        print(
            f"Total frames: "
            f"{total_frames}"
        )

        # ====================================================
        # OUTPUT WRITER
        # ====================================================

        fourcc = cv2.VideoWriter_fourcc(
            *"mp4v"
        )

        writer = cv2.VideoWriter(
            str(self.output_video_path),
            fourcc,
            fps,
            (width, height),
        )

        if not writer.isOpened():

            capture.release()

            raise RuntimeError(
                "Could not create output video."
            )

        # ====================================================
        # COUNTERS
        # ====================================================

        frame_number = 0

        processed_frames = 0

        raw_detection_count = 0

        confirmed_detection_count = 0

        try:

            while True:

                success, frame = (
                    capture.read()
                )

                if not success:

                    break

                frame_number += 1

                # =================================================
                # FRAME SKIPPING
                # =================================================

                if (
                    frame_number
                    % self.frame_skip
                    != 0
                ):

                    writer.write(
                        frame
                    )

                    continue

                processed_frames += 1

                # =================================================
                # YOLO DETECTION
                # =================================================

                detections = (
                    self.detector.detect(
                        frame
                    )
                )

                raw_detection_count += (
                    len(detections)
                )

                # =================================================
                # TRACKING
                # =================================================

                tracked_detections = (
                    self.tracker.update(
                        detections,
                        frame_number,
                    )
                )

                # =================================================
                # GPS
                # =================================================

                gps_position = (
                    self.gps_provider
                    .get_position()
                )

                # =================================================
                # CREATE ANNOTATED FRAME
                # =================================================

                annotated = frame.copy()

                # =================================================
                # DRAW DETECTIONS
                # =================================================

                for detection in (
                    tracked_detections
                ):

                    bbox = detection[
                        "bbox"
                    ]

                    xmin = int(
                        bbox["xmin"]
                    )

                    ymin = int(
                        bbox["ymin"]
                    )

                    xmax = int(
                        bbox["xmax"]
                    )

                    ymax = int(
                        bbox["ymax"]
                    )

                    confidence = (
                        detection[
                            "confidence"
                        ]
                    )

                    track_id = (
                        detection[
                            "track_id"
                        ]
                    )

                    track_hits = (
                        detection[
                            "track_hits"
                        ]
                    )

                    confirmed = (
                        detection[
                            "confirmed"
                        ]
                    )

                    # ------------------------------------------------
                    # Clamp coordinates
                    # ------------------------------------------------

                    xmin = max(
                        0,
                        min(
                            xmin,
                            width - 1,
                        ),
                    )

                    ymin = max(
                        0,
                        min(
                            ymin,
                            height - 1,
                        ),
                    )

                    xmax = max(
                        0,
                        min(
                            xmax,
                            width - 1,
                        ),
                    )

                    ymax = max(
                        0,
                        min(
                            ymax,
                            height - 1,
                        ),
                    )

                    cv2.rectangle(
                        annotated,
                        (xmin, ymin),
                        (xmax, ymax),
                        (0, 255, 0),
                        2,
                    )

                    label = (
                        f"Pothole "
                        f"T{track_id} "
                        f"{confidence:.2f}"
                    )

                    if confirmed:

                        label += (
                            " CONFIRMED"
                        )

                    else:

                        label += (
                            f" "
                            f"{track_hits}/"
                            f"{self.tracker.confirmation_hits}"
                        )

                    cv2.putText(
                        annotated,
                        label,
                        (
                            xmin,
                            max(
                                25,
                                ymin - 10,
                            ),
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 255, 0),
                        2,
                    )

                # =================================================
                # CONFIRMED TRACKS → ALERTS
                # =================================================

                for detection in (
                    tracked_detections
                ):

                    track_id = (
                        detection[
                            "track_id"
                        ]
                    )

                    if not detection[
                        "confirmed"
                    ]:

                        continue

                    confirmed_detection_count += 1

                    # ------------------------------------------------
                    # Prevent duplicate alert for same track
                    # ------------------------------------------------

                    if (
                        track_id
                        in self.alerted_tracks
                    ):

                        continue

                    # =================================================
                    # EVIDENCE
                    # =================================================

                    evidence_path = (
                        self.evidence_generator
                        .generate(
                            image=frame,
                            detections=[
                                detection
                            ],
                            image_name=(
                                f"track_"
                                f"{track_id:04d}_"
                                f"frame_"
                                f"{frame_number:06d}.jpg"
                            ),
                        )
                    )

                    evidence = Evidence(
                        image_path=str(
                            evidence_path
                        )
                    )

                    # =================================================
                    # SEVERITY
                    # =================================================

                    confidence = (
                        detection[
                            "confidence"
                        ]
                    )

                    if confidence >= 0.70:

                        severity = "high"

                    elif confidence >= 0.45:

                        severity = "medium"

                    else:

                        severity = "low"

                    # =================================================
                    # CREATE ALERT
                    # =================================================

                    alert = Alert(

                        alert_id=(
                            self.generate_alert_id()
                        ),

                        bus_id=self.bus_id,

                        timestamp=(
                            gps_position.timestamp
                        ),

                        gps={
                            "latitude":
                                gps_position.latitude,

                            "longitude":
                                gps_position.longitude,

                            "accuracy_m":
                                gps_position.accuracy_m,
                        },

                        module={
                            "type":
                                "road_defect",

                            "version":
                                "1.0",
                        },

                        severity=severity,

                        payload={

                            "defect_type":
                                "pothole",

                            "confidence":
                                confidence,

                            "track_id":
                                track_id,

                            "track_hits":
                                detection[
                                    "track_hits"
                                ],

                            "frame_number":
                                frame_number,

                            "bounding_box":
                                detection[
                                    "bbox"
                                ],

                            "image":
                                self.video_path.name,

                            "gps_source":
                                gps_position.source,
                        },

                        source={

                            "device_id":
                                self.device_id,

                            "camera_id":
                                self.camera_id,
                        },

                        evidence=evidence,
                    )

                    # =================================================
                    # LOCAL ALERT HISTORY
                    # =================================================

                    self.alerts.append(
                        alert
                    )

                    self.alert_store.save(
                        alert
                    )

                    # =================================================
                    # MARK TRACK AS ALERTED
                    # =================================================

                    self.alerted_tracks.add(
                        track_id
                    )

                    # =================================================
                    # CONSOLE
                    # =================================================

                    print(
                        "\nNEW CONFIRMED ALERT"
                    )

                    print(
                        f"  Alert ID   : "
                        f"{alert.alert_id}"
                    )

                    print(
                        f"  Track ID   : "
                        f"{track_id}"
                    )

                    print(
                        f"  Frame      : "
                        f"{frame_number}"
                    )

                    print(
                        f"  Confidence : "
                        f"{confidence:.4f}"
                    )

                    print(
                        f"  Severity   : "
                        f"{severity}"
                    )

                    print(
                        f"  GPS        : "
                        f"{gps_position.latitude}, "
                        f"{gps_position.longitude}"
                    )

                    print(
                        f"  GPS source : "
                        f"{gps_position.source}"
                    )

                    print(
                        f"  Evidence   : "
                        f"{evidence_path}"
                    )

                    print(
                        "  Local queue: "
                        "PENDING"
                    )

                # =================================================
                # OVERLAY
                # =================================================

                status = (
                    f"Frame: "
                    f"{frame_number}/"
                    f"{total_frames}"
                )

                cv2.putText(
                    annotated,
                    status,
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2,
                )

                tracker_status = (
                    f"Tracks: "
                    f"{len(self.tracker.tracks)}"
                    f"  Alerts: "
                    f"{len(self.alerts)}"
                )

                cv2.putText(
                    annotated,
                    tracker_status,
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

                gps_status = (
                    f"GPS: "
                    f"{gps_position.latitude:.6f}, "
                    f"{gps_position.longitude:.6f}"
                )

                cv2.putText(
                    annotated,
                    gps_status,
                    (20, 105),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                )

                cv2.putText(
                    annotated,
                    "EDGE MODE - LOCAL QUEUE",
                    (20, 140),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                )

                writer.write(
                    annotated
                )

                # =================================================
                # PROGRESS
                # =================================================

                if (
                    processed_frames
                    % 20
                    == 0
                ):

                    print(
                        f"Processed "
                        f"{processed_frames} "
                        f"frames | "
                        f"Raw detections: "
                        f"{raw_detection_count} | "
                        f"Confirmed observations: "
                        f"{confirmed_detection_count} | "
                        f"Alerts: "
                        f"{len(self.alerts)}"
                    )

        finally:

            capture.release()

            writer.release()

            # ----------------------------------------------------
            # Allow hardware GPS providers to clean up.
            # ----------------------------------------------------

            try:

                self.gps_provider.close()

            except Exception:

                pass

        # ========================================================
        # FINAL SUMMARY
        # ========================================================

        print(
            "\n" + "=" * 60
        )

        print(
            "EDGE VIDEO PROCESSING COMPLETE"
        )

        print(
            "=" * 60
        )

        print(
            f"Frames read            : "
            f"{frame_number}"
        )

        print(
            f"Frames processed       : "
            f"{processed_frames}"
        )

        print(
            f"Raw detections         : "
            f"{raw_detection_count}"
        )

        print(
            f"Confirmed observations : "
            f"{confirmed_detection_count}"
        )

        print(
            f"Unique alerts          : "
            f"{len(self.alerts)}"
        )

        print(
            f"GPS provider           : "
            f"{type(self.gps_provider).__name__}"
        )

        print(
            "Backend transmission   : "
            "NOT PERFORMED"
        )

        print(
            f"Local stored alerts    : "
            f"{self.alert_store.count()}"
        )

        print(
            "\nOutput video:"
        )

        print(
            self.output_video_path
        )

        print(
            "\nLocal alert file:"
        )

        print(
            self.alert_store.output_path
        )

        return self.alerts


def main():

    print("=" * 60)

    print(
        "VIDEO PROCESSOR CONFIGURATION TEST"
    )

    print("=" * 60)

    processor = VideoProcessor()

    print(
        "\nConfiguration loaded successfully."
    )

    print(
        f"\nInput video:"
        f"\n{processor.video_path}"
    )

    print(
        f"\nOutput video:"
        f"\n{processor.output_video_path}"
    )

    print(
        f"\nFrame skip:"
        f"\n{processor.frame_skip}"
    )

    print(
        f"\nConfidence:"
        f"\n{processor.confidence}"
    )

    print(
        f"\nBus ID:"
        f"\n{processor.bus_id}"
    )

    print(
        f"\nDevice ID:"
        f"\n{processor.device_id}"
    )

    print(
        f"\nCamera ID:"
        f"\n{processor.camera_id}"
    )

    print(
        f"\nGPS provider:"
        f"\n{type(processor.gps_provider).__name__}"
    )

    print(
        f"\nTracker IoU:"
        f"\n{processor.tracker.iou_threshold}"
    )

    print(
        f"\nTracker confirmation:"
        f"\n{processor.tracker.confirmation_hits}"
    )

    print(
        f"\nTracker expiry:"
        f"\n{processor.tracker.max_missing_frames}"
    )

    print(
        "\nVideoProcessor configuration test passed."
    )


if __name__ == "__main__":
    main()