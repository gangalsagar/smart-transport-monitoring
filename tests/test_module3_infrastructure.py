import unittest
import numpy as np
import tempfile
import inspect
from pathlib import Path
from datetime import datetime, timezone

from shared.camera.frame_packet import FramePacket
from shared.gps.gps_service import SharedGPSService
from shared.gps.gps_fix import GPSFix
from shared.schemas.alert_schema import Alert
from shared.config import Config

from module1_road_defect.storage.alert_queue import AlertQueue
from module1_road_defect.storage.alert_sync import AlertSync

from module3_incident_monitoring.adapter import Module3IncidentAdapter
from module3_incident_monitoring.models.rash_driving_model import RashDrivingModel
from module3_incident_monitoring.models.incident_model import IncidentDetectionModel
from module3_incident_monitoring.schemas.incident_event import IncidentEvent
from module3_incident_monitoring.plate.plate_recognizer import PlaceholderPlateRecognizer
from module3_incident_monitoring.analysis.event_confirmation import EventConfirmationManager


class TestModule3HardeningAndSafety(unittest.TestCase):

    def setUp(self):
        self.config = Config()
        self.gps_service = SharedGPSService.get_instance(config=self.config)

    def test_model_initialization_without_weights(self):
        """TEST C: Module 3 models initialize cleanly without trained weights."""
        rash_model = RashDrivingModel()
        self.assertTrue(rash_model.initialize())
        self.assertFalse(rash_model.is_trained)
        self.assertEqual(rash_model.model_name, "rash_driving_behavior_v1")

        incident_model = IncidentDetectionModel()
        self.assertTrue(incident_model.initialize())
        self.assertFalse(incident_model.is_trained)
        self.assertEqual(incident_model.model_name, "incident_accident_detector_v1")

    def test_placeholder_heuristic_metadata(self):
        """TEST D: Verify events carry explicit placeholder/heuristic metadata."""
        event = IncidentEvent(
            event_id="EVT-TEST-HEURISTIC",
            event_type="rash_driving",
            severity="high",
            assigned_team="rash_driving_team",
            inference_mode="heuristic",
            model_status="not_trained",
            detection_source="heuristic",
            plate_status="simulated",
        )
        alert_dict = event.to_alert_dict()
        p = alert_dict["payload"]

        self.assertEqual(p["inference_mode"], "heuristic")
        self.assertEqual(p["model_status"], "not_trained")
        self.assertEqual(p["detection_source"], "heuristic")
        self.assertEqual(p["plate_status"], "simulated")

    def test_model_unavailable_fallback(self):
        """TEST E: Verify model gracefully falls back when weight path is missing."""
        rash_model = RashDrivingModel(weights_path="non_existent_weights.pt")
        self.assertTrue(rash_model.initialize())
        self.assertFalse(rash_model.is_trained)
        meta = rash_model.get_metadata()
        self.assertFalse(meta["is_trained"])

    def test_consume_frame_packet(self):
        """TEST F: Module 3 Adapter consumes FramePacket cleanly."""
        adapter = Module3IncidentAdapter(config=self.config, gps_service=self.gps_service)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        packet = FramePacket(
            frame=dummy_frame,
            frame_number=1,
            timestamp=datetime.now(timezone.utc),
            video_time_seconds=0.04,
        )

        alerts = adapter.process_frame(packet)
        self.assertIsInstance(alerts, list)
        self.assertEqual(adapter.processed_frames, 1)

    def test_frame_immutability(self):
        """TEST G: Verify Module 3 processing does NOT mutate the original FramePacket frame."""
        adapter = Module3IncidentAdapter(config=self.config, gps_service=self.gps_service)
        original_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        frame_copy_hash = hash(original_frame.tobytes())

        packet = FramePacket(
            frame=original_frame,
            frame_number=10,
            timestamp=datetime.now(timezone.utc),
            video_time_seconds=0.40,
        )

        adapter.process_frame(packet)
        after_hash = hash(packet.frame.tobytes())
        self.assertEqual(frame_copy_hash, after_hash, "Original frame bytes were mutated during Module 3 processing!")

    def test_single_videocapture_ownership(self):
        """TEST H: Static inspection verifying Module 3 does not create cv2.VideoCapture."""
        import module3_incident_monitoring.adapter as adapter_mod
        src = inspect.getsource(adapter_mod)
        self.assertNotIn("cv2.VideoCapture", src, "Module 3 adapter must NOT create or manage cv2.VideoCapture!")

    def test_gps_unavailable_handling(self):
        """TEST J: Verify Module 3 builds events safely when GPS is unavailable/missing without crashing."""
        class MockUnavailableGPS:
            def get_latest_fix(self):
                return GPSFix(
                    latitude=None,
                    longitude=None,
                    accuracy_m=0.0,
                    source="unavailable",
                    status="not_started",
                    timestamp=0.0,
                )

        adapter = Module3IncidentAdapter(config=self.config, gps_service=MockUnavailableGPS())
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        packet = FramePacket(frame=dummy_frame, frame_number=1, timestamp=datetime.now(timezone.utc), video_time_seconds=0.0)

        # Build an event directly through internal builder
        pred = {"event_type": "accident", "confidence": 0.85, "bbox": [10, 10, 100, 100], "details": {}}
        event = adapter._build_event(
            event_type="accident",
            track_id=1,
            pred_dict=pred,
            frame=dummy_frame,
            frame_number=1,
            video_time_sec=0.0,
            timestamp=packet.timestamp,
        )

        self.assertIsNone(event.latitude)
        self.assertIsNone(event.longitude)
        self.assertEqual(event.gps_status, "not_started")

        # Conversion to Alert dict uses safe fallback coordinates
        alert_dict = event.to_alert_dict()
        self.assertIn("latitude", alert_dict["gps"])

    def test_plate_unreadable_and_simulated_status(self):
        """TEST K: Verify plate recognizer returns simulated/unavailable status without fake registrations."""
        recognizer = PlaceholderPlateRecognizer(mode="simulated")
        dummy_crop = np.zeros((50, 100, 3), dtype=np.uint8)
        plate_str, conf, status = recognizer.recognize_plate(dummy_crop)

        self.assertEqual(plate_str, "SIMULATED-TEST-PLATE")
        self.assertEqual(status, "simulated")

        # Test empty crop -> unavailable
        plate_none, conf_none, status_none = recognizer.recognize_plate(np.array([]))
        self.assertIsNone(plate_none)
        self.assertEqual(status_none, "unavailable")

    def test_duplicate_event_suppression(self):
        """TEST L: Verify confirmation manager suppresses candidate storms within cooldown window."""
        mgr = EventConfirmationManager(rash_min_hits=2, accident_min_hits=2, cooldown_seconds=10.0)

        # Hit 1 at t=1.0s -> not confirmed
        self.assertFalse(mgr.should_confirm_event("speeding", track_id=5, confidence=0.8, video_time_seconds=1.0))
        # Hit 2 at t=1.1s -> CONFIRMED
        self.assertTrue(mgr.should_confirm_event("speeding", track_id=5, confidence=0.8, video_time_seconds=1.1))

        # Immediate subsequent hits at t=1.2s and t=2.0s -> SUPPRESSED by 10s cooldown
        self.assertFalse(mgr.should_confirm_event("speeding", track_id=5, confidence=0.8, video_time_seconds=1.2))
        self.assertFalse(mgr.should_confirm_event("speeding", track_id=5, confidence=0.8, video_time_seconds=2.0))

        # Hit after cooldown at t=12.0s and t=12.1s -> CONFIRMED again
        self.assertFalse(mgr.should_confirm_event("speeding", track_id=5, confidence=0.8, video_time_seconds=12.0))
        self.assertTrue(mgr.should_confirm_event("speeding", track_id=5, confidence=0.8, video_time_seconds=12.1))

    def test_backend_failure_and_persistence(self):
        """TEST M: Verify events persist safely in SQLite AlertQueue when backend is offline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_queue.db"
            queue = AlertQueue(database_path=db_path)
            sync = AlertSync(backend_url="http://127.0.0.1:9999", queue=queue)  # offline port

            event = IncidentEvent(
                event_id="EVT-OFFLINE-001",
                event_type="rash_driving",
                severity="medium",
                assigned_team="rash_driving_team",
            )
            alert = Alert.model_validate(event.to_alert_dict())

            # Enqueue event
            row_id = queue.enqueue(alert)
            self.assertIsNotNone(row_id)
            self.assertEqual(queue.count("PENDING"), 1)

            # Sync attempt fails safely without losing event
            result = sync.sync()
            self.assertEqual(result["sent"], 0)
            self.assertEqual(result["failed"], 1)
            self.assertEqual(queue.count("FAILED"), 1)

    def test_critical_emergency_immediate_dispatch_and_persistence(self):
        """TEST N & O: Verify critical alerts attempt immediate sync and safely remain in queue on failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_crit_queue.db"
            queue = AlertQueue(database_path=db_path)
            sync = AlertSync(backend_url="http://127.0.0.1:9999", queue=queue)  # offline port

            event = IncidentEvent(
                event_id="EVT-CRIT-001",
                event_type="accident",
                severity="critical",
                assigned_team="emergency_team",
            )
            alert = Alert.model_validate(event.to_alert_dict())

            # Immediate sync attempt on enqueue
            row_id = queue.enqueue(alert)
            self.assertEqual(queue.count("PENDING"), 1)

            # Attempt immediate dispatch (fails because port 9999 offline)
            sent_ok = sync.send_alert(alert)
            self.assertFalse(sent_ok)
            # Event is still safe in queue
            self.assertEqual(queue.count("PENDING"), 1)


if __name__ == "__main__":
    unittest.main()
