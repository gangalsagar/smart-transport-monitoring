from pathlib import Path
from typing import List, Optional, Set
import uuid
import cv2

from shared.camera.frame_packet import FramePacket
from shared.schemas.alert_schema import Alert, Evidence, GPS, ModuleInfo, SourceInfo
from shared.config import Config
from shared.gps.gps_service import SharedGPSService
from shared.gps.gps_fix import GPSFix

from module1_road_defect.inference.detector import RoadDefectDetector
from module1_road_defect.inference.evidence import EvidenceGenerator
from module1_road_defect.inference.pothole_tracker import PotholeTracker


class Module1RoadDefectAdapter:
    """
    Adapter enabling Module 1 Road Defect Detection to process individual frames
    from the SharedVideoSource FramePacket stream without opening a separate capture,
    and consuming real location fixes from SharedGPSService.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        gps_service: Optional[SharedGPSService] = None,
        frame_skip: Optional[int] = None,
    ):
        self.config = config or Config()

        self.frame_skip = frame_skip if frame_skip is not None else int(self.config.frame_skip)
        self.confidence = float(self.config.confidence)
        self.bus_id = str(self.config.bus_id)
        self.device_id = str(self.config.device_id)
        self.camera_id = str(self.config.camera_id)

        self.detector = RoadDefectDetector(confidence=self.confidence)
        self.tracker = PotholeTracker(
            iou_threshold=float(self.config.get("module1_road_defect", "tracker", "iou_threshold", default=0.30)),
            confirmation_hits=int(self.config.get("module1_road_defect", "tracker", "confirmation_hits", default=2)),
            max_missing_frames=int(self.config.get("module1_road_defect", "tracker", "max_missing_frames", default=30)),
        )
        self.evidence_generator = EvidenceGenerator()
        self.gps_service = gps_service or SharedGPSService.get_instance(config=self.config)

        self.alerted_tracks: Set[int] = set()
        self.generated_alerts: List[Alert] = []
        self.received_frames = 0
        self.processed_frames = 0
        self.raw_detection_count = 0

    def process_frame(self, packet: FramePacket) -> List[Alert]:
        """
        Process a single FramePacket from the shared camera pipeline.
        Returns newly generated Alert objects (if any confirmed tracks occur on this frame).
        """
        frame_number = packet.frame_number
        frame = packet.frame
        height, width = frame.shape[:2]

        self.received_frames += 1

        # Apply configured frame skip
        if self.frame_skip > 1 and (frame_number % self.frame_skip != 0):
            return []

        self.processed_frames += 1

        # 1. Road defect detection (YOLO)
        detections = self.detector.detect(frame)
        self.raw_detection_count += len(detections)

        # 2. Pothole multi-frame tracking
        tracked_detections = self.tracker.update(detections, frame_number)

        # 3. Read latest Shared GPS fix
        gps_fix: GPSFix = self.gps_service.get_latest_fix()
        gps_dict = gps_fix.to_alert_gps_dict()

        new_alerts: List[Alert] = []

        # 4. Generate alerts for newly confirmed tracks
        for detection in tracked_detections:
            track_id = detection["track_id"]
            if not detection.get("confirmed", False):
                continue
            if track_id in self.alerted_tracks:
                continue

            self.alerted_tracks.add(track_id)

            # Evidence crop generation
            evidence_path = self.evidence_generator.generate(
                image=frame,
                detections=[detection],
                image_name=f"track_{track_id:04d}_frame_{frame_number:06d}.jpg",
            )
            evidence = Evidence(image_path=str(evidence_path))

            # Severity classification
            confidence = float(detection.get("confidence", 0.0))
            if confidence >= 0.70:
                severity = "high"
            elif confidence >= 0.45:
                severity = "medium"
            else:
                severity = "low"

            alert = Alert(
                alert_id=f"ALT-M1-{uuid.uuid4().hex[:8].upper()}",
                bus_id=self.bus_id,
                timestamp=packet.timestamp,
                gps=GPS(
                    latitude=gps_dict["latitude"],
                    longitude=gps_dict["longitude"],
                    accuracy_m=gps_dict["accuracy_m"],
                ),
                module=ModuleInfo(type="road_defect", version="1.0"),
                severity=severity,
                payload={
                    "defect_type": "pothole",
                    "confidence": confidence,
                    "track_id": track_id,
                    "track_hits": detection.get("track_hits", 1),
                    "frame_number": frame_number,
                    "video_time_seconds": packet.video_time_seconds,
                    "bounding_box": detection.get("bbox", {}),
                    "gps_source": gps_fix.source,
                    "gps_valid": gps_fix.valid,
                    "gps_stale": gps_fix.stale,
                    "gps_age_seconds": round(gps_fix.age_seconds, 2),
                },
                source=SourceInfo(device_id=self.device_id, camera_id=self.camera_id),
                evidence=evidence,
            )

            new_alerts.append(alert)
            self.generated_alerts.append(alert)

        return new_alerts

    def get_summary(self) -> dict:
        return {
            "received_frames": self.received_frames,
            "processed_frames": self.processed_frames,
            "raw_detections": self.raw_detection_count,
            "unique_tracks": len(self.alerted_tracks),
            "alerts_generated": len(self.generated_alerts),
        }
