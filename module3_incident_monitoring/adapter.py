from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import uuid
import cv2
import numpy as np

from shared.camera.frame_packet import FramePacket
from shared.schemas.alert_schema import Alert
from shared.config import Config
from shared.gps.gps_service import SharedGPSService
from shared.gps.gps_fix import GPSFix

from module3_incident_monitoring.config import Module3Config
from module3_incident_monitoring.schemas.incident_event import (
    IncidentEvent,
    IncidentEventType,
    IncidentSeverity,
    AssignedTeam,
)
from module3_incident_monitoring.models.rash_driving_model import RashDrivingModel
from module3_incident_monitoring.models.incident_model import IncidentDetectionModel
from module3_incident_monitoring.plate.plate_recognizer import (
    PlaceholderPlateRecognizer,
    ProductionANPRRecognizer,
    BasePlateRecognizer,
)
from module3_incident_monitoring.analysis.rash_behavior_analyzer import (
    RashBehaviorAnalyzer,
    TrackLifecycleState,
)
from module3_incident_monitoring.analysis.event_confirmation import (
    EventConfirmationManager,
    IncidentConfirmationState,
)
from module3_incident_monitoring.analysis.rolling_frame_buffer import RollingFrameBuffer

# Reuse existing Module 2 vehicle detector & tracker for high-performance edge inference
from module2_traffic.inference.detector import VehicleDetector
from module2_traffic.inference.tracker import VehicleTracker


class Module3IncidentAdapter:
    """
    Continuous Surveillance and Incident-Triggered ANPR Pipeline for Module 3.
    
    Responsibilities:
    1. Continuous Multi-Vehicle Surveillance: Every vehicle in the frame receives a unique
       track ID and continuous trajectory analysis WITHOUT executing ANPR.
    2. Multi-Frame Incident Confirmation: An incident is only promoted from SUSPICIOUS to
       CONFIRMED after satisfying multi-signal / temporal confirmation thresholds.
    3. Event-Triggered ANPR & Consensus: ANPR is ONLY invoked when incident_confirmed is True,
       sampling temporal crops from a bounded rolling buffer for OCR consensus voting.
    4. Full Incident Multi-Asset Evidence: Generates full original frame, annotated frame,
       vehicle crop, and localized plate crop.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        gps_service: Optional[SharedGPSService] = None,
        plate_recognizer: Optional[BasePlateRecognizer] = None,
        frame_skip: int = 1,
        pre_incident_frames: int = 5,
        post_incident_frames: int = 5,
    ):
        self.config = config or Config()
        self.m3_config = Module3Config(self.config)
        self.gps_service = gps_service or SharedGPSService.get_instance(config=self.config)

        self.frame_skip = frame_skip
        self.pre_incident_frames = pre_incident_frames
        self.post_incident_frames = post_incident_frames
        self.device_id = str(self.config.device_id)
        self.bus_id = str(self.config.bus_id)
        self.camera_id = str(self.config.camera_id)

        # Vehicle detector and tracker for trajectory computation
        self.detector = VehicleDetector(confidence=0.35)
        self.tracker = VehicleTracker(iou_threshold=0.30, max_missing_frames=25, confirmation_hits=2)

        # Pre-training / future-ready model interfaces
        self.rash_model = RashDrivingModel(weights_path=self.m3_config.rash_model_weights)
        self.rash_model.initialize()

        self.incident_model = IncidentDetectionModel(weights_path=self.m3_config.accident_model_weights)
        self.incident_model.initialize()

        # Event-triggered ANPR / Plate Recognizer
        if plate_recognizer is not None:
            self.plate_recognizer = plate_recognizer
        else:
            try:
                self.plate_recognizer = ProductionANPRRecognizer()
            except Exception:
                self.plate_recognizer = PlaceholderPlateRecognizer()

        # Temporal surveillance & confirmation state
        self.behavior_analyzer = RashBehaviorAnalyzer(history_window=45, max_missing_frames=20)
        self.confirmation_mgr = EventConfirmationManager(
            rash_min_hits=3,
            accident_min_hits=2,
            cooldown_seconds=15.0,
        )
        self.frame_buffer = RollingFrameBuffer(max_frames=30)

        # Evidence folder
        self.evidence_dir = self.m3_config.evidence_directory
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        self.processed_frames = 0
        self.generated_events: List[IncidentEvent] = []
        self.anpr_invocations_count = 0
        self.ocr_passes_count = 0

    def process_frame(self, packet: FramePacket) -> List[Alert]:
        """
        Process a single FramePacket from the shared camera pipeline.
        Maintains continuous tracking surveillance across all vehicles.
        ANPR is ONLY triggered on confirmed incidents.
        """
        self.processed_frames += 1
        frame_number = packet.frame_number
        frame = packet.frame
        video_time_sec = packet.video_time_seconds

        if self.frame_skip > 1 and (frame_number % self.frame_skip != 0):
            return []

        # 1. Detect and track vehicles in current frame
        raw_detections = self.detector.detect(frame)
        tracked_vehicles = self.tracker.update(raw_detections, frame_number)

        # 2. Add to bounded rolling frame buffer
        self.frame_buffer.add_frame(frame_number, video_time_sec, frame, tracked_vehicles)

        # 3. Continuous Surveillance: Update trajectory and behavior history per active vehicle (NO ANPR)
        features_by_track = self.behavior_analyzer.update_tracks(
            tracked_vehicles,
            video_time_sec,
            frame_number,
        )

        # 4. Behavioral Feature Inference (Rash Driving Model - Disabled by default in Accident-Only mode)
        candidate_predictions: List[Dict[str, Any]] = []
        if self.m3_config.rash_driving_detection_enabled:
            for track_id, feat_dict in features_by_track.items():
                preds = self.rash_model.infer(feat_dict)
                for p in preds:
                    p["track_id"] = track_id
                    candidate_predictions.append(p)

        # 5. Collision / Accident Overlap & Interaction Analysis
        if self.m3_config.accident_detection_enabled:
            overlaps = self._find_track_overlaps(tracked_vehicles)
            incident_input = {
                "frame": frame,
                "overlapping_tracks": overlaps,
                "tracked_vehicles": tracked_vehicles,
            }
            incident_preds = self.incident_model.infer(incident_input)
            candidate_predictions.extend(incident_preds)

        # 6. Incident Confirmation Gate: Filter candidates through temporal multi-signal gate
        confirmed_alerts: List[Alert] = []

        for pred in candidate_predictions:
            event_type = pred.get("event_type", "unknown_incident")
            track_id = pred.get("track_id")
            conf = float(pred.get("confidence", 0.0))

            # STRICT GATE: Requires multi-frame confirmation
            if not self.confirmation_mgr.should_confirm_event(event_type, track_id, conf, video_time_sec):
                continue

            # 7. EVENT-TRIGGERED ANPR & MULTI-ASSET EVIDENCE GENERATION
            event = self._build_confirmed_incident_event(
                event_type=event_type,
                track_id=track_id,
                pred_dict=pred,
                frame=frame,
                frame_number=frame_number,
                video_time_sec=video_time_sec,
                timestamp=packet.timestamp,
                tracked_vehicles=tracked_vehicles,
            )

            self.confirmation_mgr.mark_reported(event_type, track_id)
            self.generated_events.append(event)

            # Convert to standard Alert schema for shared AlertQueue ingestion
            alert_dict = event.to_alert_dict()
            alert_obj = Alert.model_validate(alert_dict)
            confirmed_alerts.append(alert_obj)

        return confirmed_alerts

    def _find_track_overlaps(self, tracked_vehicles: List[Dict[str, Any]]) -> List[Tuple[int, int, float]]:
        """Calculate pairwise IoU overlap among tracked vehicle bounding boxes."""
        overlaps = []
        n = len(tracked_vehicles)
        for i in range(n):
            for j in range(i + 1, n):
                v1, v2 = tracked_vehicles[i], tracked_vehicles[j]
                t1, t2 = v1.get("track_id"), v2.get("track_id")
                b1 = self._to_bbox_list(v1.get("bbox"))
                b2 = self._to_bbox_list(v2.get("bbox"))
                iou = self._calculate_iou(b1, b2)
                if iou > 0.10:
                    overlaps.append((t1, t2, iou))
        return overlaps

    @staticmethod
    def _to_bbox_list(raw_bbox: Any) -> List[int]:
        if isinstance(raw_bbox, dict):
            return [
                int(raw_bbox.get("xmin", 0)),
                int(raw_bbox.get("ymin", 0)),
                int(raw_bbox.get("xmax", 0)),
                int(raw_bbox.get("ymax", 0)),
            ]
        elif isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) == 4:
            return [int(x) for x in raw_bbox]
        return [0, 0, 0, 0]

    @staticmethod
    def _calculate_iou(boxA: List[int], boxB: List[int]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
        boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
        unionArea = boxAArea + boxBArea - interArea
        return interArea / unionArea if unionArea > 0 else 0.0

    def _extract_crops_for_track(self, track_id: int, target_frame: int) -> List[np.ndarray]:
        """Collect vehicle crops across the temporal window around target_frame."""
        crops = []
        window = self.frame_buffer.get_window_frames(
            target_frame,
            pre_frames=self.pre_incident_frames,
            post_frames=self.post_incident_frames,
        )
        for (f_no, t_sec, f_img, tracks) in window:
            for trk in tracks:
                if trk.get("track_id") == track_id:
                    bbox = self._to_bbox_list(trk.get("bbox"))
                    if len(bbox) == 4:
                        xmin, ymin, xmax, ymax = bbox
                        h, w = f_img.shape[:2]
                        xmin, ymin = max(0, xmin), max(0, ymin)
                        xmax, ymax = min(w, xmax), min(h, ymax)
                        if (xmax > xmin + 15) and (ymax > ymin + 15):
                            crops.append(f_img[ymin:ymax, xmin:xmax].copy())
        return crops

    def _build_confirmed_incident_event(
        self,
        event_type: str,
        track_id: Optional[int],
        pred_dict: Dict[str, Any],
        frame: np.ndarray,
        frame_number: int,
        video_time_sec: float,
        timestamp,
        tracked_vehicles: Optional[List[Dict[str, Any]]] = None,
    ) -> IncidentEvent:
        """Construct full IncidentEvent with team assignment, GPS, ANPR consensus, and evidence."""
        # 1. Routing and Severity determination
        if event_type in {"accident", "collision", "emergency_obstacle"}:
            assigned_team: AssignedTeam = "emergency_team"
            severity: IncidentSeverity = "critical" if pred_dict.get("confidence", 0) > 0.8 else "high"
        else:
            assigned_team: AssignedTeam = "rash_driving_team"
            severity: IncidentSeverity = "high" if event_type in {"speeding", "wrong_way"} else "medium"

        # 2. Shared GPS fix association
        gps_fix: GPSFix = self.gps_service.get_latest_fix()

        # 3. Resolve vehicle bbox for the primary involved vehicle
        bbox = pred_dict.get("bbox")
        if not bbox and track_id is not None and tracked_vehicles:
            for v in tracked_vehicles:
                if v.get("track_id") == track_id:
                    bbox = self._to_bbox_list(v.get("bbox"))
                    break

        # 4. Multi-Asset Evidence Generation
        evidence_rel_path = None
        annotated_rel_path = None
        full_frame_rel_path = None
        plate_crop_rel_path = None

        plate_str = None
        plate_conf = 0.0
        plate_stat = "unavailable"
        consensus_metadata: Dict[str, Any] = {}

        event_id = f"EVT-M3-{uuid.uuid4().hex[:8].upper()}"

        h, w = frame.shape[:2]

        # A. Full Resolution Incident Frame
        full_frame_filename = f"{event_id}_full_f{frame_number:06d}.jpg"
        full_frame_path = self.evidence_dir / full_frame_filename
        cv2.imwrite(str(full_frame_path), frame)
        full_frame_rel_path = str(full_frame_path)

        # B. Involved Vehicle Crop & Temporal ANPR Consensus
        primary_crop = None
        if bbox and len(bbox) == 4:
            xmin, ymin, xmax, ymax = bbox
            xmin, ymin = max(0, int(xmin)), max(0, int(ymin))
            xmax, ymax = min(w, int(xmax)), min(h, int(ymax))

            if (xmax > xmin) and (ymax > ymin):
                primary_crop = frame[ymin:ymax, xmin:xmax].copy()
                veh_crop_filename = f"{event_id}_veh_trk{track_id or 0}.jpg"
                veh_crop_path = self.evidence_dir / veh_crop_filename
                cv2.imwrite(str(veh_crop_path), primary_crop)
                evidence_rel_path = str(veh_crop_path)

                # TRIGGER EVENT ANPR (Only on confirmed incident!)
                if self.m3_config.plate_recognition_enabled:
                    self.anpr_invocations_count += 1
                    # Extract temporal crops from buffer for voting
                    temporal_crops = self._extract_crops_for_track(track_id or 0, frame_number)
                    if not temporal_crops:
                        temporal_crops = [primary_crop]
                    self.ocr_passes_count += len(temporal_crops)

                    # Temporal consensus voting
                    plate_str, plate_conf, plate_stat, consensus_metadata = (
                        self.plate_recognizer.recognize_plate_temporal(temporal_crops)
                    )

                    # Extract localized plate crop if supported
                    if hasattr(self.plate_recognizer, "locate_plate_crop"):
                        p_crop = self.plate_recognizer.locate_plate_crop(primary_crop)
                        if p_crop is not None and p_crop.size > 0:
                            plate_crop_filename = f"{event_id}_plate.jpg"
                            plate_crop_path = self.evidence_dir / plate_crop_filename
                            cv2.imwrite(str(plate_crop_path), p_crop)
                            plate_crop_rel_path = str(plate_crop_path)

        # C. Annotated Incident Image
        annotated_frame = frame.copy()
        if bbox and len(bbox) == 4:
            xmin, ymin, xmax, ymax = bbox
            xmin, ymin = max(0, int(xmin)), max(0, int(ymin))
            xmax, ymax = min(w, int(xmax)), min(h, int(ymax))
            # Draw involved vehicle box
            color = (0, 0, 255) if assigned_team == "emergency_team" else (0, 165, 255)
            cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), color, 2)

            label = f"{event_type.upper()} | Trk#{track_id or 0}"
            if plate_str:
                label += f" | {plate_str}"
            cv2.putText(
                annotated_frame,
                label,
                (xmin, max(20, ymin - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

        annotated_filename = f"{event_id}_annotated.jpg"
        annotated_path = self.evidence_dir / annotated_filename
        cv2.imwrite(str(annotated_path), annotated_frame)
        annotated_rel_path = str(annotated_path)

        # Determine involved tracks list
        colliding_tracks = pred_dict.get("details", {}).get("colliding_tracks", [])
        involved_tracks = list(set([track_id] + colliding_tracks)) if track_id is not None else []

        return IncidentEvent(
            event_id=event_id,
            event_type=event_type,  # type: ignore
            severity=severity,
            assigned_team=assigned_team,
            status="new",
            timestamp=timestamp,
            latitude=gps_fix.latitude if gps_fix.valid else None,
            longitude=gps_fix.longitude if gps_fix.valid else None,
            gps_accuracy_m=gps_fix.accuracy_m if gps_fix.valid else 0.0,
            gps_source=gps_fix.source,
            gps_status=gps_fix.status,
            vehicle_track_id=track_id,
            plate_number=plate_str,
            plate_confidence=plate_conf,
            plate_status=plate_stat,
            model_confidence=float(pred_dict.get("confidence", 0.75)),
            inference_mode="heuristic",
            model_status="not_trained",
            detection_source="heuristic",
            evidence_image_path=evidence_rel_path or annotated_rel_path or full_frame_rel_path,
            payload={
                "frame_number": frame_number,
                "video_time_seconds": video_time_sec,
                "involved_track_ids": involved_tracks,
                "full_frame_evidence": full_frame_rel_path,
                "annotated_evidence": annotated_rel_path,
                "plate_crop_evidence": plate_crop_rel_path,
                "consensus_metadata": consensus_metadata,
                "prediction_details": pred_dict.get("details", {}),
                "is_trained_model": False,
                "model_description": "Continuous Surveillance & Incident-Triggered ANPR Pipeline",
            },
            device_id=self.device_id,
            bus_id=self.bus_id,
            camera_id=self.camera_id,
        )

    # Backward compatibility alias for test suite
    _build_event = _build_confirmed_incident_event

    def get_telemetry(self) -> Dict[str, Any]:
        """Return operational telemetry for the surveillance pipeline."""
        return {
            "processed_frames": self.processed_frames,
            "unique_tracks_surveilled": self.behavior_analyzer.total_unique_tracks_surveilled,
            "active_tracks_current": self.behavior_analyzer.get_active_track_count(),
            "suspicious_candidates_evaluated": len(self.confirmation_mgr._candidate_hits),
            "confirmed_incidents_total": len(self.generated_events),
            "anpr_invocations_event_triggered": self.anpr_invocations_count,
            "ocr_passes_executed": self.ocr_passes_count,
        }
