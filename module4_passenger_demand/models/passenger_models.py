from datetime import datetime, date
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class PassRecord(BaseModel):
    """
    Physical bus pass registered with the transport authority.
    Privacy note: Personal details (name/phone/address) are never exposed.
    """
    pass_id: str
    passenger_category: str = "general"     # student | senior | general | employee | disabled
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    allowed_routes: Optional[list[str]] = None  # None means valid on all routes
    status: str = "active"                  # active | suspended | expired | cancelled
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """
    Outcome of validating a pass entry.
    """
    status: Literal["valid", "invalid", "suspicious"]
    reason: Optional[str] = None  # pass_not_found | pass_expired | route_not_allowed | abnormal_submission_rate | duplicate_submission | capacity_exceeded
    pass_record: Optional[PassRecord] = None


class BoardingEvent(BaseModel):
    """
    Unified Passenger Boarding Event for both Ticket and Physical Pass transactions.
    """
    event_id: str
    bus_id: str
    route_id: str
    timestamp: datetime
    boarding_stop_id: Optional[str] = "STOP-GENERIC"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    passenger_type: Literal["ticket", "pass"]
    pass_id: Optional[str] = None
    pass_id_hash: Optional[str] = None      # Tokenized/hashed identifier for privacy preservation
    ticket_id: Optional[str] = None
    
    validation_status: Literal["valid", "suspicious", "invalid"] = "valid"
    validation_reason: Optional[str] = None
    source: str = "conductor_terminal"      # conductor_terminal | mock_etm | etm_api
    confidence: float = 1.0


class RouteDemandMetric(BaseModel):
    route_id: str
    total_boardings: int
    ticket_boardings: int
    pass_boardings: int
    capacity: int
    load_factor: float
    status: Literal["low", "normal", "high", "critical"]
    recommendation: Optional[str] = None


class HourlyDemandMetric(BaseModel):
    hour: int
    hour_label: str
    boardings: int
    is_peak: bool = False
    load_factor: float
