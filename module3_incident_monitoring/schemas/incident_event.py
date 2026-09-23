from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal


IncidentEventType = Literal[
    "rash_driving",
    "speeding",
    "sudden_lane_change",
    "tailgating",
    "wrong_way",
    "accident",
    "collision",
    "vehicle_breakdown",
    "emergency_obstacle",
    "unknown_incident",
]

IncidentSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical",
]

AssignedTeam = Literal[
    "rash_driving_team",
    "emergency_team",
]

IncidentStatus = Literal[
    "new",
    "acknowledged",
    "in_progress",
    "dispatched",
    "resolved",
    "closed",
]


@dataclass
class IncidentEvent:
    """
    Standardized Module 3 Incident Event data model.

    Attributes:
        event_id: Unique event identifier (e.g., 'EVT-INC-XXXXX')
        event_type: Category of incident (rash_driving, accident, etc.)
        severity: Priority level (low, medium, high, critical)
        assigned_team: Team routing target ('rash_driving_team' | 'emergency_team')
        status: Current lifecycle state (new, acknowledged, in_progress, etc.)
        timestamp: UTC event occurrence time
        latitude: Latitude in decimal degrees (None if GPS fix unavailable)
        longitude: Longitude in decimal degrees (None if GPS fix unavailable)
        gps_accuracy_m: GPS horizontal accuracy in meters
        gps_source: Source of location fix (e.g. 'windows_laptop_location')
        gps_status: Informational status of GPS fix ('ok', 'stale', 'unavailable', etc.)
        vehicle_track_id: ID of the primary vehicle involved (if tracked)
        plate_number: Recognized alphanumeric license plate string (if detected)
        plate_confidence: OCR confidence score (0.0 to 1.0)
        model_confidence: Event classification confidence score (0.0 to 1.0)
        evidence_image_path: Relative path to cropped evidence image on edge disk
        payload: Additional metrics (trajectory, speed estimation, sensor values, etc.)
        device_id: Edge device hardware identifier
        bus_id: Vehicle / transport identifier
        camera_id: Camera identifier
    """
    event_id: str
    event_type: IncidentEventType
    severity: IncidentSeverity
    assigned_team: AssignedTeam
    status: IncidentStatus = "new"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy_m: float = 0.0
    gps_source: str = "unknown"
    gps_status: str = "unavailable"

    vehicle_track_id: Optional[int] = None
    plate_number: Optional[str] = None
    plate_confidence: float = 0.0
    plate_status: str = "unavailable"  # 'unavailable' | 'simulated' | 'detected_unreadable' | 'recognized'
    model_confidence: float = 0.0
    inference_mode: str = "heuristic"  # 'placeholder' | 'heuristic' | 'trained'
    model_status: str = "not_trained"  # 'not_trained' | 'mock' | 'heuristic' | 'trained'
    detection_source: str = "heuristic"  # 'simulated' | 'heuristic' | 'trained_model'
    evidence_image_path: Optional[str] = None

    payload: Dict[str, Any] = field(default_factory=dict)
    device_id: str = "EDGE-01"
    bus_id: str = "BUS-TEST"
    camera_id: str = "FRONT_CAM"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary representation."""
        data = asdict(self)
        ts = self.timestamp if self.timestamp is not None else datetime.now(timezone.utc)
        data["timestamp"] = ts.isoformat()
        return data

    def to_alert_dict(self, default_lat: float = 12.9716, default_lng: float = 77.5946) -> Dict[str, Any]:
        """
        Convert this incident event into an Alert-compatible dictionary
        for seamless ingestion by the existing AlertQueue, AlertSyncWorker,
        and FastAPI backend endpoints without schema changes.
        """
        lat = self.latitude if (self.latitude is not None) else default_lat
        lng = self.longitude if (self.longitude is not None) else default_lng
        ts = self.timestamp if self.timestamp is not None else datetime.now(timezone.utc)

        alert_payload = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "assigned_team": self.assigned_team,
            "status": self.status,
            "vehicle_track_id": self.vehicle_track_id,
            "plate_number": self.plate_number,
            "plate_confidence": self.plate_confidence,
            "plate_status": self.plate_status,
            "model_confidence": self.model_confidence,
            "inference_mode": self.inference_mode,
            "model_status": self.model_status,
            "detection_source": self.detection_source,
            "gps_source": self.gps_source,
            "gps_status": self.gps_status,
            **self.payload,
        }

        alert_data = {
            "alert_id": self.event_id,
            "bus_id": self.bus_id,
            "timestamp": ts.isoformat(),
            "gps": {
                "latitude": float(lat),
                "longitude": float(lng),
                "accuracy_m": float(self.gps_accuracy_m if self.gps_accuracy_m > 0 else 5.0),
            },
            "module": {
                "type": "incident_anpr",
                "version": "1.0",
            },
            "severity": self.severity,
            "payload": alert_payload,
            "source": {
                "device_id": self.device_id,
                "camera_id": self.camera_id,
            },
            "evidence": {"image_path": self.evidence_image_path} if self.evidence_image_path else None,
        }

        return alert_data
