import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from module2_traffic.inference.detector import VehicleDetector
from module2_traffic.inference.tracker import VehicleTracker
from module2_traffic.inference.counter import VehicleCounter
from module2_traffic.inference.traffic_analyzer import TrafficAnalyzer
from module1_road_defect.storage.alert_queue import AlertQueue
from module1_road_defect.storage.alert_sync import AlertSync
import backend.app.main as main_module
from shared.schemas.alert_schema import Alert, GPS, ModuleInfo, SourceInfo, Evidence


class TestModule2Traffic(unittest.TestCase):
    """
    Comprehensive test suite for Module 2 (Traffic Monitoring):
    A. Vehicle Detector initialization and config
    B. Vehicle Tracker multi-object track lifecycle
    C. Vehicle Counter virtual line-crossing & class counts
    D. Traffic Analyzer congestion levels (LOW/MEDIUM/HIGH/CRITICAL)
    E. Traffic Event Schema validation
    F. Offline Queue persistence
    G. AlertSync upload & idempotency
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "traffic_test_queue.db"
        self.alert_file = self.temp_path / "backend_traffic_alerts.jsonl"
        self.evidence_dir = self.temp_path / "backend_evidence"

        self.patch_alert_file = patch.object(main_module, "ALERT_FILE", self.alert_file)
        self.patch_evidence_dir = patch.object(main_module, "EVIDENCE_DIRECTORY", self.evidence_dir)
        self.patch_alert_file.start()
        self.patch_evidence_dir.start()

        self.queue = AlertQueue(database_path=self.db_path)
        self.sync = AlertSync(backend_url="http://127.0.0.1:8001", queue=self.queue)

    def tearDown(self):
        self.patch_alert_file.stop()
        self.patch_evidence_dir.stop()
        self.temp_dir.cleanup()

    def test_detector_initialization(self):
        detector = VehicleDetector()
        self.assertTrue(detector.model_path.exists())
        self.assertGreater(detector.confidence, 0.0)
        self.assertIn("car", detector.allowed_classes)
        self.assertIn("bus", detector.allowed_classes)
        self.assertIn("truck", detector.allowed_classes)
        self.assertIn("motorbike", detector.allowed_classes)

    def test_tracker_lifecycle(self):
        tracker = VehicleTracker(iou_threshold=0.3, confirmation_hits=2, max_missing_frames=5)
        d1 = [{"class_name": "car", "confidence": 0.85, "bbox": {"xmin": 100, "ymin": 100, "xmax": 200, "ymax": 200}}]
        r1 = tracker.update(d1, frame_number=1)
        self.assertEqual(len(r1), 1)
        self.assertFalse(r1[0]["confirmed"])
        track_id = r1[0]["track_id"]

        d2 = [{"class_name": "car", "confidence": 0.88, "bbox": {"xmin": 105, "ymin": 105, "xmax": 205, "ymax": 205}}]
        r2 = tracker.update(d2, frame_number=2)
        self.assertEqual(r2[0]["track_id"], track_id)
        self.assertTrue(r2[0]["confirmed"])

    def test_counter_line_crossing(self):
        counter = VehicleCounter(line_ratio=0.5)
        h = 200  # line at y=100

        # Before line (y=80)
        counter.update([{"track_id": 1, "class_name": "car", "confirmed": True, "centroid": (150, 80)}], h)
        self.assertEqual(counter.total_count, 0)

        # Crossed line (y=120)
        summary = counter.update([{"track_id": 1, "class_name": "car", "confirmed": True, "centroid": (150, 120)}], h)
        self.assertEqual(summary["total_count"], 1)
        self.assertEqual(summary["class_counts"]["car"], 1)
        self.assertEqual(summary["directional_counts"]["direction_a"], 1)

        # Same track moving further does not increment
        summary2 = counter.update([{"track_id": 1, "class_name": "car", "confirmed": True, "centroid": (150, 150)}], h)
        self.assertEqual(summary2["total_count"], 1)

    def test_traffic_analyzer_congestion(self):
        analyzer = TrafficAnalyzer(low_threshold=5, medium_threshold=12, high_threshold=20)
        
        low = analyzer.analyze(active_vehicle_count=3, total_counted=5, class_counts={"car": 5}, directional_counts={}, frame_width=640, frame_height=480, detections=[])
        self.assertEqual(low["congestion_level"], "low")

        med = analyzer.analyze(active_vehicle_count=8, total_counted=10, class_counts={"car": 10}, directional_counts={}, frame_width=640, frame_height=480, detections=[])
        self.assertEqual(med["congestion_level"], "medium")

        high = analyzer.analyze(active_vehicle_count=15, total_counted=20, class_counts={"car": 20}, directional_counts={}, frame_width=640, frame_height=480, detections=[])
        self.assertEqual(high["congestion_level"], "high")

        crit = analyzer.analyze(active_vehicle_count=25, total_counted=35, class_counts={"car": 35}, directional_counts={}, frame_width=640, frame_height=480, detections=[])
        self.assertEqual(crit["congestion_level"], "critical")

    def test_traffic_event_schema_and_queue(self):
        event = Alert(
            alert_id="TRF-TEST-0001",
            bus_id="BUS-TEST",
            timestamp=datetime.now(timezone.utc),
            gps=GPS(latitude=12.9716, longitude=77.5946, accuracy_m=3.5),
            module=ModuleInfo(type="traffic", version="1.0"),
            severity="medium",
            payload={
                "defect_type": "traffic_congestion",
                "vehicle_count": 14,
                "vehicle_classes": {"car": 10, "bus": 2, "truck": 2, "motorcycle": 0},
                "active_vehicle_count": 8,
                "density": "medium",
                "congestion_level": "medium",
            },
            source=SourceInfo(device_id="EDGE-01", camera_id="FRONT_CAM"),
        )

        # Enqueue
        inserted1 = self.queue.enqueue(event)
        self.assertTrue(inserted1)

        # Deduplication in queue
        inserted2 = self.queue.enqueue(event)
        self.assertFalse(inserted2)

        # Read back
        pending = self.queue.get_pending(limit=10)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0][1].module.type, "traffic")

    def test_traffic_backend_sync_and_idempotency(self):
        event = Alert(
            alert_id="TRF-IDEM-001",
            bus_id="BUS-TEST",
            timestamp=datetime.now(timezone.utc),
            gps=GPS(latitude=12.9716, longitude=77.5946, accuracy_m=3.5),
            module=ModuleInfo(type="traffic", version="1.0"),
            severity="high",
            payload={"defect_type": "traffic_congestion", "vehicle_count": 22},
            source=SourceInfo(device_id="EDGE-01", camera_id="FRONT_CAM"),
        )

        # Ingestion 1
        is_new1 = main_module.save_alert(event)
        self.assertTrue(is_new1)

        # Ingestion 2 (duplicate)
        is_new2 = main_module.save_alert(event)
        self.assertFalse(is_new2)

        saved = main_module.load_alerts()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].alert_id, "TRF-IDEM-001")
        self.assertEqual(saved[0].module.type, "traffic")


if __name__ == "__main__":
    unittest.main()
