import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from shared.gps.gps_fix import GPSFix
from shared.gps.gps_provider import GPSProvider
from shared.gps.gps_service import SharedGPSService
from shared.gps.mobile_provider import MobileGPSProvider


class MockFixedGPSProvider(GPSProvider):
    def __init__(self, lat=12.6637, lng=77.4538, valid=True):
        self.lat = lat
        self.lng = lng
        self._valid = valid
        self._started = False

    @property
    def name(self) -> str:
        return "mock_fixed"

    @property
    def source_name(self) -> str:
        return "mock_fixed_source"

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def get_location(self) -> GPSFix:
        return GPSFix(
            latitude=self.lat,
            longitude=self.lng,
            altitude=0.0,
            accuracy_m=10.0,
            timestamp=datetime.now(timezone.utc),
            source=self.source_name,
            valid=self._valid,
            provider=self.name,
            status="ok" if self._valid else "error",
        )


class TestSharedGPSArchitecture(unittest.TestCase):

    def test_gps_fix_model(self):
        fix = GPSFix(
            latitude=12.6637,
            longitude=77.4538,
            accuracy_m=5.0,
            source="windows_laptop_location",
            valid=True,
            provider="laptop",
            status="ok",
        )
        self.assertTrue(fix.valid)
        self.assertFalse(fix.stale)
        self.assertAlmostEqual(fix.latitude, 12.6637, places=4)
        self.assertAlmostEqual(fix.longitude, 77.4538, places=4)
        
        gps_dict = fix.to_alert_gps_dict()
        self.assertIn("latitude", gps_dict)
        self.assertIn("longitude", gps_dict)
        self.assertIn("accuracy_m", gps_dict)
        self.assertEqual(gps_dict["latitude"], 12.6637)

    def test_gps_service_lifecycle_and_singleton(self):
        mock_prov = MockFixedGPSProvider(lat=12.9716, lng=77.5946, valid=True)
        service = SharedGPSService(
            provider=mock_prov,
            poll_interval_seconds=0.1,
            stale_threshold_seconds=5.0,
        )

        service.start()
        self.assertTrue(service.is_running)

        fix = service.get_latest_fix()
        self.assertTrue(fix.valid)
        self.assertAlmostEqual(fix.latitude, 12.9716, places=4)
        self.assertAlmostEqual(fix.longitude, 77.5946, places=4)
        self.assertEqual(fix.source, "mock_fixed_source")

        service.stop()
        self.assertFalse(service.is_running)

    def test_mobile_provider_stub(self):
        mobile = MobileGPSProvider()
        mobile.start()
        fix = mobile.get_location()
        self.assertFalse(fix.valid)
        self.assertEqual(fix.provider, "mobile")
        self.assertEqual(fix.source, "mobile_gps_bridge")
        mobile.stop()


if __name__ == "__main__":
    unittest.main()
