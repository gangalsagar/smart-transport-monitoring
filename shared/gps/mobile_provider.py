from datetime import datetime, timezone
from typing import Optional

from shared.gps.gps_provider import GPSProvider
from shared.gps.gps_fix import GPSFix


class MobileGPSProvider(GPSProvider):
    """
    Future-ready Mobile GPS Bridge provider.
    Serves as an interface contract for mobile app telemetry integration.
    """

    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint
        self._is_running = False

    @property
    def name(self) -> str:
        return "mobile"

    @property
    def source_name(self) -> str:
        return "mobile_gps_bridge"

    def start(self) -> None:
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False

    def get_location(self) -> GPSFix:
        """
        Placeholder implementation returning safe unavailable fix until mobile bridge is active.
        """
        now = datetime.now(timezone.utc)
        return GPSFix(
            latitude=None,
            longitude=None,
            timestamp=now,
            source=self.source_name,
            valid=False,
            stale=False,
            provider=self.name,
            status="not_implemented",
            error_message="Mobile GPS provider interface is prepared for future integration.",
        )
