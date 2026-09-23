from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.request import Request, urlopen
import json


# ============================================================
# GPS POSITION
# ============================================================

@dataclass
class GPSPosition:

    latitude: float
    longitude: float
    accuracy_m: float
    timestamp: datetime
    source: str = "unknown"


# ============================================================
# PROVIDER INTERFACE
# ============================================================

class GPSProvider:

    def get_position(self) -> GPSPosition:
        raise NotImplementedError


# ============================================================
# SIMULATED GPS
# ============================================================

class SimulatedGPSProvider(GPSProvider):
    """
    Moving GPS provider for development/testing.
    """

    def __init__(
        self,
        latitude=12.9716,
        longitude=77.5946,
        accuracy_m=3.5,
        latitude_step=0.00005,
        longitude_step=0.00006,
    ):

        self.latitude = latitude
        self.longitude = longitude
        self.accuracy_m = accuracy_m

        self.latitude_step = latitude_step
        self.longitude_step = longitude_step

        self.call_count = 0

    def get_position(self):

        position = GPSPosition(
            latitude=self.latitude,
            longitude=self.longitude,
            accuracy_m=self.accuracy_m,
            timestamp=datetime.now(timezone.utc),
            source="simulated",
        )

        self.latitude += self.latitude_step
        self.longitude += self.longitude_step

        self.call_count += 1

        return position


# ============================================================
# PHONE GPS
# ============================================================

class PhoneGPSProvider(GPSProvider):
    """
    GPS provider for the demonstration mobile edge device.

    The phone exposes a small HTTP endpoint such as:

        http://PHONE_IP:9000/gps

    Expected response:

        {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "accuracy_m": 4.2,
            "timestamp": "2026-08-31T15:20:00Z"
        }

    The provider converts the phone response into the same
    GPSPosition object used by the rest of Module 1.
    """

    def __init__(
        self,
        endpoint: str,
        timeout: float = 3.0,
        max_age_seconds: float = 10.0,
    ):

        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.max_age_seconds = max_age_seconds

        self.last_position: Optional[GPSPosition] = None

    def get_position(self) -> GPSPosition:

        request = Request(
            self.endpoint,
            headers={
                "Accept": "application/json"
            },
            method="GET",
        )

        try:

            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                if response.status != 200:

                    raise RuntimeError(
                        f"Phone GPS returned HTTP "
                        f"{response.status}"
                    )

                body = (
                    response.read()
                    .decode("utf-8")
                )

                data = json.loads(body)

        except Exception as exc:

            # Keep the most recent valid position if
            # the phone temporarily becomes unavailable.

            if self.last_position is not None:

                return self.last_position

            raise RuntimeError(
                f"Unable to read phone GPS: {exc}"
            ) from exc

        try:

            latitude = float(
                data["latitude"]
            )

            longitude = float(
                data["longitude"]
            )

            accuracy = float(
                data.get(
                    "accuracy_m",
                    data.get(
                        "accuracy",
                        0.0
                    )
                )
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:

            raise RuntimeError(
                f"Invalid phone GPS response: {exc}"
            ) from exc

        timestamp = self._parse_timestamp(
            data.get("timestamp")
        )

        position = GPSPosition(
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy,
            timestamp=timestamp,
            source="phone",
        )

        self.last_position = position

        return position

    @staticmethod
    def _parse_timestamp(
        value
    ) -> datetime:

        if not value:

            return datetime.now(
                timezone.utc
            )

        try:

            timestamp = datetime.fromisoformat(
                str(value).replace(
                    "Z",
                    "+00:00"
                )
            )

            if timestamp.tzinfo is None:

                timestamp = timestamp.replace(
                    tzinfo=timezone.utc
                )

            return timestamp.astimezone(
                timezone.utc
            )

        except (
            ValueError,
            TypeError,
        ):

            return datetime.now(
                timezone.utc
            )


# ============================================================
# GNSS PROVIDER
# ============================================================

class SerialGNSSProvider(GPSProvider):
    """
    Future dedicated GNSS receiver interface.

    This intentionally does not implement serial parsing yet.
    The rest of Module 1 only depends on GPSProvider.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 2.0,
    ):

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

    def get_position(self) -> GPSPosition:

        raise NotImplementedError(
            "Dedicated GNSS serial provider is "
            "reserved for hardware integration."
        )


# ============================================================
# GPS FACTORY
# ============================================================

def create_gps_provider(
    mode: str = "simulated",
    phone_endpoint: str = "http://127.0.0.1:9000/gps",
    phone_timeout: float = 3.0,
    phone_max_age_seconds: float = 10.0,
    gnss_port: str = "COM3",
    gnss_baudrate: int = 9600,
    gnss_timeout: float = 2.0,
) -> GPSProvider:

    normalized_mode = (
        mode.strip().lower()
    )

    if normalized_mode == "simulated":

        return SimulatedGPSProvider()

    if normalized_mode == "phone":

        return PhoneGPSProvider(
            endpoint=phone_endpoint,
            timeout=phone_timeout,
            max_age_seconds=phone_max_age_seconds,
        )

    if normalized_mode == "gnss":

        return SerialGNSSProvider(
            port=gnss_port,
            baudrate=gnss_baudrate,
            timeout=gnss_timeout,
        )

    raise ValueError(
        f"Unsupported GPS mode: {mode}"
    )


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 60)
    print("GPS PROVIDER TEST")
    print("=" * 60)

    print("\nSimulated provider:")

    gps = create_gps_provider(
        mode="simulated"
    )

    print(
        f"  Type   : {type(gps).__name__}"
    )

    position = gps.get_position()

    print(
        f"  GPS    : "
        f"{position.latitude:.6f}, "
        f"{position.longitude:.6f}"
    )

    print(
        f"  Source : {position.source}"
    )

    print("\nPhone provider configuration:")

    phone = create_gps_provider(
        mode="phone",
        phone_endpoint="http://127.0.0.1:9000/gps",
    )

    print(
        f"  Type     : {type(phone).__name__}"
    )

    print(
        f"  Endpoint : {phone.endpoint}"
    )

    print(
        f"  Timeout  : {phone.timeout}s"
    )

    print("\nGNSS provider configuration:")

    gnss = create_gps_provider(
        mode="gnss",
        gnss_port="COM3",
        gnss_baudrate=9600,
    )

    print(
        f"  Type     : {type(gnss).__name__}"
    )

    print(
        f"  Port     : {gnss.port}"
    )

    print(
        f"  Baudrate : {gnss.baudrate}"
    )

# ============================================================
# SHARED GPS SERVICE ADAPTER
# ============================================================

class SharedGPSProviderAdapter(GPSProvider):
    """
    Adapter allowing standalone Module 1 video processor to read from
    the centralized SharedGPSService (Windows Laptop Location).
    """

    def __init__(self, gps_service=None):
        from shared.gps.gps_service import SharedGPSService
        self.gps_service = gps_service or SharedGPSService.get_instance()

    def get_position(self) -> GPSPosition:
        from shared.gps.gps_fix import GPSFix
        fix: GPSFix = self.gps_service.get_latest_fix()
        if fix.valid and fix.latitude is not None and fix.longitude is not None:
            return GPSPosition(
                latitude=fix.latitude,
                longitude=fix.longitude,
                accuracy_m=fix.accuracy_m,
                timestamp=fix.timestamp,
                source=fix.source,
            )
        return GPSPosition(
            latitude=12.9716,
            longitude=77.5946,
            accuracy_m=5.0,
            timestamp=datetime.now(timezone.utc),
            source=fix.source,
        )


if __name__ == "__main__":

    main()