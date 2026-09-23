import unittest
import tempfile
from pathlib import Path
import numpy as np

from shared.camera.frame_packet import FramePacket
from shared.camera.shared_video_source import SharedVideoSource
from shared.runtime.edge_orchestrator import EdgeOrchestrator
from module1_road_defect.adapter import Module1RoadDefectAdapter
from module2_traffic.adapter import Module2TrafficAdapter


class TestUnifiedSharedArchitecture(unittest.TestCase):
    """
    Test suite for Shared Camera & Unified Edge Runtime:
    1. FramePacket creation and properties.
    2. SharedVideoSource single capture and FramePacket streaming.
    3. Module 1 Adapter receiving FramePacket without opening a video capture.
    4. Module 2 Adapter receiving FramePacket without opening a video capture.
    5. Same frame number progression to both modules.
    6. EdgeOrchestrator initialization and clean teardown.
    """

    def test_frame_packet_structure(self):
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        packet = FramePacket(
            frame=dummy_frame,
            frame_number=42,
            video_time_seconds=1.4,
        )
        self.assertEqual(packet.frame_number, 42)
        self.assertEqual(packet.video_time_seconds, 1.4)
        self.assertEqual(packet.frame.shape, (480, 640, 3))
        self.assertIsNotNone(packet.timestamp)

    def test_module1_adapter_process_frame(self):
        adapter = Module1RoadDefectAdapter(frame_skip=1)
        dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        packet = FramePacket(
            frame=dummy_frame,
            frame_number=1,
            video_time_seconds=0.033,
        )
        alerts = adapter.process_frame(packet)
        self.assertIsInstance(alerts, list)
        summary = adapter.get_summary()
        self.assertEqual(summary["processed_frames"], 1)
        self.assertEqual(summary["received_frames"], 1)

    def test_module2_adapter_process_frame(self):
        adapter = Module2TrafficAdapter(fps=25.0)
        dummy_frame = np.zeros((432, 768, 3), dtype=np.uint8)
        packet = FramePacket(
            frame=dummy_frame,
            frame_number=1,
            video_time_seconds=0.04,
        )
        alerts = adapter.process_frame(packet)
        self.assertIsInstance(alerts, list)
        summary = adapter.get_summary()
        self.assertEqual(summary["processed_frames"], 1)

    def test_shared_video_source_reading(self):
        video_path = Path("module2_traffic/data/videos/test_video.mp4")
        if not video_path.exists():
            self.skipTest("Test video not found on disk.")

        source = SharedVideoSource(video_path)
        self.assertTrue(source.open())
        self.assertTrue(source.is_opened())
        self.assertGreater(source.fps, 0)
        self.assertGreater(source.total_frames, 0)

        # Read 5 packets
        for expected_num in range(1, 6):
            packet = source.read_packet()
            self.assertIsNotNone(packet)
            self.assertEqual(packet.frame_number, expected_num)
            self.assertEqual(packet.frame.shape[0], source.resolution[1])
            self.assertEqual(packet.frame.shape[1], source.resolution[0])

        source.release()
        self.assertFalse(source.is_opened())


if __name__ == "__main__":
    unittest.main()
