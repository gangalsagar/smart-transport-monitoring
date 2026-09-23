import hashlib
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from module4_passenger_demand.models.passenger_models import BoardingEvent, ValidationResult
from module4_passenger_demand.services.pass_validator import PassValidator
from module4_passenger_demand.services.data_quality_service import DataQualityService

logger = logging.getLogger(__name__)


class BoardingService:
    """
    Coordinates ticket transactions, physical pass validations, privacy tokenization,
    and data quality auditing into a canonical BoardingEvent stream.
    """
    def __init__(
        self,
        validator: PassValidator,
        data_quality: DataQualityService,
    ):
        self.validator = validator
        self.data_quality = data_quality

    def process_pass_entry(
        self,
        pass_id: str,
        bus_id: str,
        route_id: str,
        stop_id: str = "STOP-GENERIC",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> BoardingEvent:
        ts = timestamp or datetime.now()
        val_res: ValidationResult = self.validator.validate_pass(
            pass_id=pass_id,
            current_route_id=route_id,
            check_time=ts
        )

        event_id = f"pass_ev_{uuid.uuid4().hex[:10]}"
        # Privacy tokenization: Hash the pass number for privacy preservation in analytical logs
        pass_id_clean = pass_id.strip().upper() if pass_id else ""
        pass_hash = hashlib.sha256(pass_id_clean.encode("utf-8")).hexdigest()[:16] if pass_id_clean else None

        event = BoardingEvent(
            event_id=event_id,
            bus_id=bus_id,
            route_id=route_id,
            timestamp=ts,
            boarding_stop_id=stop_id,
            latitude=latitude,
            longitude=longitude,
            passenger_type="pass",
            pass_id=pass_id_clean,
            pass_id_hash=pass_hash,
            validation_status=val_res.status,
            validation_reason=val_res.reason,
            source="conductor_terminal",
            confidence=1.0 if val_res.status == "valid" else 0.4
        )

        # Audit with data quality service (checks bursts, duplicates, capacity)
        audited_event = self.data_quality.audit_boarding_event(event)
        return audited_event

    def process_ticket_entry(
        self,
        ticket_id: str,
        bus_id: str,
        route_id: str,
        stop_id: str = "STOP-GENERIC",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        source: str = "etm_terminal",
    ) -> BoardingEvent:
        ts = timestamp or datetime.now()
        event_id = f"tkt_ev_{uuid.uuid4().hex[:10]}"

        event = BoardingEvent(
            event_id=event_id,
            bus_id=bus_id,
            route_id=route_id,
            timestamp=ts,
            boarding_stop_id=stop_id,
            latitude=latitude,
            longitude=longitude,
            passenger_type="ticket",
            ticket_id=ticket_id,
            validation_status="valid",
            validation_reason="ticket_issued",
            source=source,
            confidence=1.0
        )

        audited_event = self.data_quality.audit_boarding_event(event)
        return audited_event
