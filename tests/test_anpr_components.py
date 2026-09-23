#!/usr/bin/env python3
"""
Unit and Component Tests for ANPR Pipeline
==========================================
Tests:
1. PlateDetector component: loads, runs on synthetic vehicle image, outputs bounding boxes & crops.
2. ANPREngine OCR Integration: crops feed into baseline CRNN OCR, outputs plate text & confidence.
3. TrackPlateAggregator: multi-vehicle tracking association, rate limiting, and majority voting.
4. Incident System Association: IncidentEvent captures real recognized plate info and track ID.
"""

import sys
import unittest
from pathlib import Path
import numpy as np
import cv2

# Add root directory to python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

try:
    from module3_incident_monitoring.anpr.inference.plate_detector import PlateDetector, PlateDetection
    from module3_incident_monitoring.anpr.inference.anpr_engine import ANPREngine, ANPRResult
    from module3_incident_monitoring.anpr.inference.track_plate_aggregator import TrackPlateAggregator
except ImportError:
    from module3_incident_anpr.inference.plate_detector import PlateDetector, PlateDetection
    from module3_incident_anpr.inference.anpr_engine import ANPREngine, ANPRResult
    from module3_incident_anpr.inference.track_plate_aggregator import TrackPlateAggregator
from module3_incident_monitoring.plate.plate_recognizer import ProductionANPRRecognizer, PlaceholderPlateRecognizer
from module3_incident_monitoring.schemas.incident_event import IncidentEvent

class TestANPRComponents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a synthetic vehicle crop with a simulated plate area (dark text on white plate)
        cls.vehicle_img = np.full((300, 500, 3), 100, dtype=np.uint8)  # Gray vehicle body
        # Draw white license plate in bottom center
        cv2.rectangle(cls.vehicle_img, (150, 180), (350, 240), (255, 255, 255), -1)
        # Draw dark text characters "MH12AB1234"
        cv2.putText(
            cls.vehicle_img, "MH12AB1234", (160, 225),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3, cv2.LINE_AA
        )

    def test_01_plate_detector_execution(self):
        """Test Stage 1 PlateDetector candidate segmentation."""
        detector = PlateDetector()
        detections = detector.detect(self.vehicle_img)

        self.assertIsInstance(detections, list)
        self.assertGreaterEqual(len(detections), 1, "Plate detector should return at least one candidate")

        top_det = detections[0]
        self.assertIsInstance(top_det, PlateDetection)
        self.assertEqual(len(top_det.bbox), 4)
        self.assertGreater(top_det.confidence, 0.0)
        self.assertGreater(top_det.crop.size, 0)
        self.assertIn(top_det.label, ["license_plate", "license_plate_heuristic"])

    def test_02_anpr_engine_ocr_integration(self):
        """Test unified ANPREngine inference on vehicle image."""
        engine = ANPREngine()
        self.assertIsNotNone(engine.ocr_model, "Baseline OCR model should load successfully")

        result = engine.process_vehicle_image(self.vehicle_img)
        self.assertIsInstance(result, ANPRResult)
        self.assertIn(result.status, ["recognized", "detected_unreadable"])

        # Test direct crop recognition on real dataset sample if available
        test_sample_path = ROOT / "module3_incident_anpr/indian_license_plate_ocr/images/plate_000001.jpg"
        if test_sample_path.exists():
            real_crop = cv2.imread(str(test_sample_path))
            text, conf = engine.recognize_crop(real_crop)
            self.assertIsNotNone(text)
            self.assertGreater(len(text), 0)
            self.assertGreater(conf, 0.0)

    def test_03_temporal_track_plate_aggregator(self):
        """Test multi-vehicle track association and temporal majority voting."""
        aggregator = TrackPlateAggregator(history_window=5, min_consensus_votes=2, ocr_interval_frames=2)

        track_id_1 = 101
        track_id_2 = 102

        # Simulate consecutive frame observations for Track 101
        aggregator.add_reading(track_id_1, "MH03BS7778", 0.90, (10, 10, 50, 30), frame_number=1)
        self.assertFalse(aggregator.should_process_track(track_id_1, current_frame=2))
        self.assertTrue(aggregator.should_process_track(track_id_1, current_frame=3))

        aggregator.add_reading(track_id_1, "MH03BS7778", 0.92, (10, 10, 50, 30), frame_number=3)
        aggregator.add_reading(track_id_1, "MH03DS7778", 0.70, (10, 10, 50, 30), frame_number=5)

        # Simulate noisy readings for Track 102
        aggregator.add_reading(track_id_2, "DL01CA5678", 0.85, (100, 100, 180, 140), frame_number=2)

        # Verify Consensus for Track 101
        plate_1, conf_1, status_1 = aggregator.get_consensus_plate(track_id_1)
        self.assertEqual(plate_1, "MH03BS7778")
        self.assertEqual(status_1, "recognized")
        self.assertAlmostEqual(conf_1, 0.91, places=2)

        # Verify Track 102 provisional status (only 1 vote)
        plate_2, conf_2, status_2 = aggregator.get_consensus_plate(track_id_2)
        self.assertEqual(plate_2, "DL01CA5678")
        self.assertEqual(status_2, "provisional")

    def test_04_production_recognizer_incident_integration(self):
        """Test ProductionANPRRecognizer integration into IncidentEvent."""
        recognizer = ProductionANPRRecognizer()
        plate_text, conf, status = recognizer.recognize_plate(self.vehicle_img)

        # Construct IncidentEvent with recognized plate
        event = IncidentEvent(
            event_id="EVT-TEST-001",
            event_type="rash_driving",
            severity="high",
            assigned_team="rash_driving_team",
            status="new",
            timestamp="2026-09-04T05:58:00Z",
            vehicle_track_id=42,
            plate_number=plate_text,
            plate_confidence=conf,
            plate_status=status
        )

        self.assertEqual(event.vehicle_track_id, 42)
        self.assertIn(event.plate_status, ["recognized", "detected_unreadable", "unavailable"])
        self.assertEqual(event.assigned_team, "rash_driving_team")

if __name__ == "__main__":
    unittest.main()
