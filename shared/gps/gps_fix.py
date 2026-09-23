from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any


@dataclass
class GPSFix:
    """
    Standardized location fix data model across all providers and modules.

    Attributes:
        latitude: Latitude in decimal degrees (None if invalid/unavailable)
        longitude: Longitude in decimal degrees (None if invalid/unavailable)
        altitude: Altitude in meters above sea level (optional)
        accuracy_m: Horizontal accuracy radius in meters
        timestamp: Time the location reading was acquired (UTC)
        source: Origin identifier (e.g. 'windows_laptop_location', 'mobile_gps_bridge')
        valid: True if coordinates represent a real valid fix
        stale: True if the fix age exceeds the configured staleness threshold
        provider: Name of the active GPS provider implementation
        status: Informational status string ('ok', 'waiting', 'permission_denied', 'error', 'unavailable')
        error_message: Error description if valid is False
        extra: Additional metadata (e.g. heading, speed, raw satellite stats)
    """
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = 0.0
    accuracy_m: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "unknown"
    valid: bool = False
    stale: bool = False
    provider: str = "unknown"
    status: str = "unavailable"
    error_message: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        """Calculate the age of this GPS fix relative to current UTC time."""
        now = datetime.now(timezone.utc)
        if self.timestamp.tzinfo is None:
            ts = self.timestamp.replace(tzinfo=timezone.utc)
        else:
            ts = self.timestamp
        return max(0.0, (now - ts).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize fix to dictionary for alert payloads and JSON logs."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["age_seconds"] = round(self.age_seconds, 2)
        return data

    def to_alert_gps_dict(self, default_lat: float = 12.9716, default_lng: float = 77.5946) -> Dict[str, Any]:
        """
        Convert to format compatible with shared.schemas.alert_schema.GPS.
        If fix is not valid, uses safe coordinates to avoid breaking validation.
        """
        lat = self.latitude if (self.valid and self.latitude is not None) else default_lat
        lng = self.longitude if (self.valid and self.longitude is not None) else default_lng
        acc = self.accuracy_m if (self.valid and self.accuracy_m > 0) else 5.0

        return {
            "latitude": float(lat),
            "longitude": float(lng),
            "accuracy_m": float(acc),
        }
