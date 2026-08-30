
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any
from datetime import datetime


# -----------------------------
# GPS Information
# -----------------------------
class GPS(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float = Field(..., ge=0)


# -----------------------------
# Module Information
# -----------------------------
class ModuleInfo(BaseModel):
    type: Literal[
        "road_defect",
        "traffic",
        "incident_anpr"
    ]
    version: str = "1.0"


# -----------------------------
# Source Device Information
# -----------------------------
class SourceInfo(BaseModel):
    device_id: str
    camera_id: str


# -----------------------------
# Optional Evidence
# -----------------------------
class Evidence(BaseModel):
    image_path: Optional[str] = None


# -----------------------------
# Main Alert Schema
# -----------------------------
class Alert(BaseModel):
    alert_id: str
    bus_id: str
    timestamp: datetime

    gps: GPS
    module: ModuleInfo

    severity: Literal[
        "low",
        "medium",
        "high",
        "critical"
    ]

    payload: Dict[str, Any]

    source: SourceInfo
    evidence: Optional[Evidence] = None