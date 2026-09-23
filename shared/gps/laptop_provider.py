import asyncio
from datetime import datetime, timezone
from typing import Optional

from shared.gps.gps_provider import GPSProvider
from shared.gps.gps_fix import GPSFix


class LaptopGPSProvider(GPSProvider):
    """
    Windows Laptop Location Provider using Windows Location Services via winsdk,
    with automatic real-time network geolocation resolution fallback.
    """

    def __init__(self, accuracy_request_m: float = 10.0):
        self._accuracy_request_m = accuracy_request_m
        self._geolocator = None
        self._is_running = False
        self._winsdk_available = False

    @property
    def name(self) -> str:
        return "laptop"

    @property
    def source_name(self) -> str:
        return "windows_laptop_location"

    def start(self) -> None:
        """Initialize the location provider."""
        try:
            from winsdk.windows.devices.geolocation import Geolocator, PositionAccuracy
            self._geolocator = Geolocator()
            try:
                self._geolocator.desired_accuracy = PositionAccuracy.HIGH
            except Exception:
                pass
            self._winsdk_available = True
            self._is_running = True
        except ImportError:
            self._winsdk_available = False
            self._is_running = True
        except Exception:
            self._winsdk_available = False
            self._is_running = True

    def stop(self) -> None:
        """Release geolocator reference."""
        self._geolocator = None
        self._is_running = False

    def get_location(self) -> GPSFix:
        """
        Query location safely without throwing uncaught exceptions.
        Attempts native Windows SDK if present, then falls back to network geolocation.
        """
        now = datetime.now(timezone.utc)

        if not self._is_running:
            return GPSFix(
                latitude=None,
                longitude=None,
                timestamp=now,
                source=self.source_name,
                valid=False,
                provider=self.name,
                status="not_started",
                error_message="Location provider is not started.",
            )

        # Primary: winsdk (if native library is available)
        if self._winsdk_available and self._geolocator is not None:
            try:
                async def _fetch():
                    pos = await self._geolocator.get_geoposition_async()
                    return pos

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            position = executor.submit(lambda: asyncio.run(_fetch())).result(timeout=4.0)
                    else:
                        position = loop.run_until_complete(_fetch())
                except RuntimeError:
                    position = asyncio.run(_fetch())

                if position and position.coordinate and position.coordinate.point:
                    coord_point = position.coordinate.point.position
                    lat = float(coord_point.latitude)
                    lng = float(coord_point.longitude)
                    alt = float(coord_point.altitude) if coord_point.altitude is not None else 0.0
                    accuracy_m = 5.0
                    try:
                        if hasattr(position.coordinate, "accuracy") and position.coordinate.accuracy is not None:
                            accuracy_m = float(position.coordinate.accuracy)
                    except Exception:
                        pass

                    return GPSFix(
                        latitude=lat,
                        longitude=lng,
                        altitude=alt,
                        accuracy_m=accuracy_m,
                        timestamp=now,
                        source=self.source_name,
                        valid=True,
                        stale=False,
                        provider=self.name,
                        status="ok",
                        error_message=None,
                        extra={"sensor": "windows_sensor"},
                    )
            except Exception:
                pass

        # Secondary: Real-time network geolocation
        fallback_fix = self._fetch_network_location(now)
        if fallback_fix is not None:
            return fallback_fix

        return GPSFix(
            latitude=None,
            longitude=None,
            timestamp=now,
            source=self.source_name,
            valid=False,
            provider=self.name,
            status="no_fix",
            error_message="Location resolution unavailable.",
        )

    def _fetch_network_location(self, now: datetime) -> Optional[GPSFix]:
        """Query real-time network geolocation services."""
        import json
        import urllib.request

        # Endpoint 1: ip-api
        try:
            req = urllib.request.Request("http://ip-api.com/json", headers={"User-Agent": "SmartTransport/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "success":
                    lat = float(data["lat"])
                    lng = float(data["lon"])
                    return GPSFix(
                        latitude=lat,
                        longitude=lng,
                        altitude=0.0,
                        accuracy_m=15.0,
                        timestamp=now,
                        source=self.source_name,
                        valid=True,
                        stale=False,
                        provider=self.name,
                        status="ok",
                        error_message=None,
                        extra={"method": "network", "city": data.get("city")},
                    )
        except Exception:
            pass

        # Endpoint 2: ipinfo
        try:
            req = urllib.request.Request("https://ipinfo.io/json", headers={"User-Agent": "SmartTransport/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                loc = data.get("loc", "").split(",")
                if len(loc) == 2:
                    lat = float(loc[0])
                    lng = float(loc[1])
                    return GPSFix(
                        latitude=lat,
                        longitude=lng,
                        altitude=0.0,
                        accuracy_m=25.0,
                        timestamp=now,
                        source=self.source_name,
                        valid=True,
                        stale=False,
                        provider=self.name,
                        status="ok",
                        error_message=None,
                        extra={"method": "network", "city": data.get("city")},
                    )
        except Exception:
            pass

        return None
