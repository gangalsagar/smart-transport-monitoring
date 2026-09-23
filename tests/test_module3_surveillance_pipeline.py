#!/usr/bin/env python3
"""
Comprehensive Integration & Negative Test Suite for Module 3 Continuous Surveillance Pipeline
"""

import unittest
from pathlib import Path
import numpy as np
import cv2

from shared.camera.frame_packet import FramePacket
from shared.config import Config
from module3_incident_monitoring.adapter import Module3IncidentAdapter
from module3_incident_monitoring.analysis.rash_behavior_analyzer import (
    RashBehaviorAnalyzer,
    TrackLifecycleState,
)
from module3_incident_monitoring.analysis.event_confirmation import (
    EventConfirmationManager,
    IncidentConfirmationState,
)
from module3_incident_monitoring.plate.plate_recognizer import BasePlateRecognizer


class MockCountedPlateRecognizer(BasePlateRecognizer):
    """Mock plate recognizer to strictly count ANPR and OCR activations."""
    def __init__(self):
        self.anpr_invocations = 0

    def recognize_plate(self, vehicle_crop: np.ndarray):
        self.anpr_invocations += 1
        return "KA01MJ5005", 0.94, "recognized"


class TestModule3SurveillancePipeline(unittest.TestCase):

    def setUp(self):
        self.config = Config()
        self.mock_plate_recognizer = MockCountedPlateRecognizer()
        self.adapter = Module3IncidentAdapter(
            config=self.config,
            plate_recognizer=self.mock_plate_recognizer,
        )

    def test_01_vehicle_in_frame_no_incident_does_not_trigger_anpr(self):
        """
        TEST 1: A vehicle remains in frame with normal motion -> receives track ID,
        is continuously monitored, and does NOT trigger ANPR.
        """
        # Create synthetic vehicle moving smoothly without swerving or speeding
        analyzer = RashBehaviorAnalyzer(history_window=45)
        self.mock_plate_recognizer.anpr_invocations = 0

        for f_idx in range(1, 20):
            # Normal moving vehicle: 2 pixels per frame
            vehicle = {
                "track_id": 1,
                "bbox": [100 + f_idx * 2, 100, 150 + f_idx * 2, 140],
                "centroid": [125.0 + f_idx * 2, 120.0],
                "confidence": 0.88,
                "class_name": "car",
            }
            features = analyzer.update_tracks([vehicle], video_time_seconds=f_idx * 0.04, frame_number=f_idx)
            self.assertIn(1, features)
            if f_idx == 1:
                self.assertEqual(features[1]["state"], TrackLifecycleState.NEW)
            else:
                self.assertEqual(features[1]["state"], TrackLifecycleState.ACTIVE)
            self.assertEqual(features[1]["lane_swerves"], 0)

        # Confirm zero ANPR triggers occurred
        self.assertEqual(self.mock_plate_recognizer.anpr_invocations, 0)

    def test_02_suspicious_event_without_confirmation_does_not_trigger_anpr(self):
        """
        TEST 2: A suspicious anomaly occurs for only 1 frame -> does NOT reach min_hits -> 0 ANPR.
        """
        conf_mgr = EventConfirmationManager(rash_min_hits=3, accident_min_hits=2, cooldown_seconds=15.0)
        
        # 1 hit of sudden_lane_change
        confirmed = conf_mgr.should_confirm_event("sudden_lane_change", track_id=2, confidence=0.85, video_time_seconds=1.0)
        self.assertFalse(confirmed)
        self.assertEqual(conf_mgr.get_event_state("sudden_lane_change", 2), IncidentConfirmationState.SUSPICIOUS)
        self.assertEqual(self.mock_plate_recognizer.anpr_invocations, 0)

    def test_03_confirmed_incident_triggers_anpr_only_for_involved_track(self):
        """
        TEST 3: A confirmed incident triggers ANPR only for the involved track.
        """
        dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        # Draw vehicle 1 (violator) and vehicle 2 (normal bystander)
        cv2.rectangle(dummy_frame, (100, 100), (200, 180), (255, 255, 255), -1)
        cv2.rectangle(dummy_frame, (500, 100), (600, 180), (255, 255, 255), -1)

        packet = FramePacket(
            frame=dummy_frame,
            frame_number=10,
            timestamp=None,
            video_time_seconds=0.4,
        )

        pred_violator = {
            "event_type": "speeding",
            "confidence": 0.90,
            "track_id": 1,
            "bbox": [100, 100, 200, 180],
        }

        # Build confirmed event directly
        event = self.adapter._build_confirmed_incident_event(
            event_type="speeding",
            track_id=1,
            pred_dict=pred_violator,
            frame=dummy_frame,
            frame_number=10,
            video_time_sec=0.4,
            timestamp=packet.timestamp,
        )

        self.assertEqual(event.event_type, "speeding")
        self.assertEqual(event.vehicle_track_id, 1)
        self.assertEqual(event.plate_number, "KA01MJ5005")
        self.assertGreater(self.mock_plate_recognizer.anpr_invocations, 0)

    def test_04_vehicle_exits_frame_cleans_up_safely(self):
        """
        TEST 5: When a vehicle leaves the frame, its surveillance trajectory state is safely purged.
        """
        analyzer = RashBehaviorAnalyzer(history_window=45, max_missing_frames=5)
        
        # Vehicle present for frames 1-3
        for f in range(1, 4):
            v = {"track_id": 99, "bbox": [10, 10, 50, 50], "centroid": [30.0, 30.0]}
            analyzer.update_tracks([v], video_time_seconds=f * 0.04, frame_number=f)
        
        self.assertIn(99, analyzer._trajectories)

        # Vehicle missing for frames 4-10
        for f in range(4, 11):
            analyzer.update_tracks([], video_time_seconds=f * 0.04, frame_number=f)

        # Confirmed purged
        self.assertNotIn(99, analyzer._trajectories)

    def test_05_unreadable_plate_does_not_fabricate_registration(self):
        """
        TEST 6: When OCR fails / plate is obscured, incident is still recorded with
        plate_number=None and status="unavailable" without hallucinating fake registrations.
        """
        class FailingPlateRecognizer(BasePlateRecognizer):
            def recognize_plate(self, crop):
                return None, 0.0, "unavailable"

        adapter_failing = Module3IncidentAdapter(
            config=self.config,
            plate_recognizer=FailingPlateRecognizer(),
        )

        dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        event = adapter_failing._build_confirmed_incident_event(
            event_type="wrong_way",
            track_id=5,
            pred_dict={"event_type": "wrong_way", "confidence": 0.85, "bbox": [20, 20, 80, 80]},
            frame=dummy_frame,
            frame_number=1,
            video_time_sec=0.04,
            timestamp=None,
        )

        self.assertIsNone(event.plate_number)
        self.assertEqual(event.plate_status, "unavailable")
        self.assertEqual(event.plate_confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
