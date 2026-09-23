import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import backend.app.main as main_module
from module1_road_defect.storage.alert_queue import AlertQueue
from module1_road_defect.storage.alert_sync import AlertSync
from shared.schemas.alert_schema import Alert, GPS, ModuleInfo, SourceInfo, Evidence


class TestAlertSyncIdempotency(unittest.TestCase):
    """
    Test suite proving that AlertSync retrying the same alert
    or re-synchronizing already accepted alerts does not create
    duplicate backend records.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_queue.db"
        self.alert_file = self.temp_path / "backend_alerts.jsonl"
        self.evidence_dir = self.temp_path / "backend_evidence"

        # Patch backend storage
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

    def _create_sample_alert(self, alert_id="ALT-SYNC-001"):
        return Alert(
            alert_id=alert_id,
            bus_id="BUS-TEST",
            timestamp=datetime.now(timezone.utc),
            gps=GPS(latitude=12.9716, longitude=77.5946, accuracy_m=3.5),
            module=ModuleInfo(type="road_defect", version="1.0"),
            severity="high",
            payload={
                "defect_type": "pothole",
                "confidence": 0.88,
                "track_id": 1,
                "frame_number": 100,
            },
            source=SourceInfo(device_id="EDGE-01", camera_id="FRONT_CAM"),
        )

    def test_alert_sync_retry_produces_single_backend_record(self):
        """
        Prove that sending the same alert via AlertSync twice
        produces exactly one record in the backend storage.
        """
        alert = self._create_sample_alert("ALT-SYNC-RETRY-001")

        # Mock the network transmission to directly call the backend save_alert
        def mock_send_alert_json(alert_to_send):
            is_new = main_module.save_alert(alert_to_send)
            return True

        with patch.object(self.sync, "_send_alert_json", side_effect=mock_send_alert_json):
            # First send
            success1 = self.sync.send_alert(alert)
            self.assertTrue(success1)

            # Second send (retry)
            success2 = self.sync.send_alert(alert)
            self.assertTrue(success2)

        # Verify backend storage has exactly ONE record
        saved = main_module.load_alerts()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].alert_id, "ALT-SYNC-RETRY-001")

    def test_edge_queue_idempotency(self):
        """
        Investigate and verify that AlertQueue.enqueue rejects duplicate alert_id insertion.
        """
        alert = self._create_sample_alert("ALT-QUEUE-001")

        # 1st enqueue -> newly inserted
        inserted1 = self.queue.enqueue(alert)
        self.assertTrue(inserted1)

        # 2nd enqueue -> already exists, ignored
        inserted2 = self.queue.enqueue(alert)
        self.assertFalse(inserted2)

        # Queue total should be exactly 1
        summary = self.queue.summary()
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["pending"], 1)


if __name__ == "__main__":
    unittest.main()
