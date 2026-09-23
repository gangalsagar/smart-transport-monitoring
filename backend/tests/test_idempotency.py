import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.main import app
from shared.schemas.alert_schema import Alert, GPS, ModuleInfo, SourceInfo, Evidence


class TestBackendIdempotency(unittest.TestCase):
    """
    Test suite proving that the backend alert endpoints are idempotent.
    Sending the same alert multiple times produces exactly one record in storage.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.alert_file = self.temp_path / "alerts.jsonl"
        self.evidence_dir = self.temp_path / "evidence"

        # Patch storage locations to use temporary test directories
        self.patch_alert_file = patch.object(main_module, "ALERT_FILE", self.alert_file)
        self.patch_evidence_dir = patch.object(main_module, "EVIDENCE_DIRECTORY", self.evidence_dir)

        self.patch_alert_file.start()
        self.patch_evidence_dir.start()

        self.client = TestClient(app)

    def tearDown(self):
        self.patch_alert_file.stop()
        self.patch_evidence_dir.stop()
        self.temp_dir.cleanup()

    def _create_sample_alert(self, alert_id="ALT-TEST-0001"):
        return Alert(
            alert_id=alert_id,
            bus_id="BUS-TEST",
            timestamp=datetime.now(timezone.utc),
            gps=GPS(latitude=12.9716, longitude=77.5946, accuracy_m=3.5),
            module=ModuleInfo(type="road_defect", version="1.0"),
            severity="high",
            payload={
                "defect_type": "pothole",
                "confidence": 0.85,
                "track_id": 1,
                "frame_number": 100,
            },
            source=SourceInfo(device_id="EDGE-01", camera_id="FRONT_CAM"),
            evidence=Evidence(image_path="test_evidence.jpg"),
        )

    def test_post_alerts_json_idempotent(self):
        """
        POST /alerts twice with the exact same alert_id.
        Verification:
        - 1st POST returns accepted with duplicate=False
        - 2nd POST returns accepted with duplicate=True
        - backend storage contains exactly ONE record
        """
        alert = self._create_sample_alert("ALT-IDEM-001")
        payload = alert.model_dump(mode="json")

        # 1st POST
        resp1 = self.client.post("/alerts", json=payload)
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertEqual(data1["status"], "accepted")
        self.assertEqual(data1["alert_id"], "ALT-IDEM-001")
        self.assertFalse(data1.get("duplicate"))

        # 2nd POST with exact same alert
        resp2 = self.client.post("/alerts", json=payload)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2["status"], "accepted")
        self.assertEqual(data2["alert_id"], "ALT-IDEM-001")
        self.assertTrue(data2.get("duplicate"))

        # Verify storage contains only 1 record
        saved_alerts = main_module.load_alerts()
        self.assertEqual(len(saved_alerts), 1)
        self.assertEqual(saved_alerts[0].alert_id, "ALT-IDEM-001")

        # Verify GET /alerts
        get_resp = self.client.get("/alerts")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["count"], 1)

    def test_post_alerts_with_evidence_idempotent(self):
        """
        POST /alerts/with-evidence twice with the exact same alert_id and image.
        Verification:
        - 1st POST returns accepted with duplicate=False
        - 2nd POST returns accepted with duplicate=True
        - backend storage contains exactly ONE record
        - evidence image is saved properly
        """
        alert = self._create_sample_alert("ALT-IDEM-002")
        alert_json_str = alert.model_dump_json()

        image_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00"

        # 1st POST with evidence
        resp1 = self.client.post(
            "/alerts/with-evidence",
            data={"alert": alert_json_str},
            files={"evidence": ("track_0001_frame_000100_evidence.jpg", io.BytesIO(image_content), "image/jpeg")},
        )
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertEqual(data1["status"], "accepted")
        self.assertFalse(data1.get("duplicate"))

        # 2nd POST with same alert
        resp2 = self.client.post(
            "/alerts/with-evidence",
            data={"alert": alert_json_str},
            files={"evidence": ("track_0001_frame_000100_evidence.jpg", io.BytesIO(image_content), "image/jpeg")},
        )
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2["status"], "accepted")
        self.assertTrue(data2.get("duplicate"))

        # Verify storage count is 1
        saved_alerts = main_module.load_alerts()
        self.assertEqual(len(saved_alerts), 1)
        self.assertEqual(saved_alerts[0].alert_id, "ALT-IDEM-002")


if __name__ == "__main__":
    unittest.main()
