import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from shared.config import Config
from shared.schemas.alert_schema import Alert, ModuleInfo, SourceInfo, GPS
from shared.gps.gps_service import SharedGPSService

from module4_passenger_demand.models.passenger_models import BoardingEvent
from module4_passenger_demand.providers.pass_registry import PassRegistry, FilePassDataProvider
from module4_passenger_demand.providers.ticketing_provider import MockTicketingProvider
from module4_passenger_demand.services.pass_validator import PassValidator
from module4_passenger_demand.services.data_quality_service import DataQualityService
from module4_passenger_demand.services.boarding_service import BoardingService

logger = logging.getLogger(__name__)


class Module4PassengerDemandAdapter:
    """
    Edge adapter for Module 4 — Passenger Demand Intelligence.
    
    Architectural characteristics:
    - Dedicated to DATA-DRIVEN passenger ticketing & pass events.
    - DOES NOT consume video frames (video remains dedicated to Modules 1, 2, and 3).
    - Bridges physical pass validations and ticketing transactions to the unified edge AlertQueue.
    - Leverages SharedGPSService for spatial context when recording boarding events.
    """
    def __init__(
        self,
        config: Optional[Config] = None,
        gps_service: Optional[SharedGPSService] = None,
    ):
        self.config = config or Config()
        self.gps_service = gps_service
        self.enabled = self.config.module4_enabled

        # Identify bus and default route
        self.bus_id = self.config.passenger_bus_id
        self.default_route_id = self.config.passenger_default_route_id
        self.bus_capacity = self.config.passenger_bus_capacity

        # Providers & Services
        dataset_path = self.config.resolve_path(self.config.passenger_dataset_path)
        data_provider = FilePassDataProvider(dataset_path)
        self.registry = PassRegistry(provider=data_provider)
        
        self.validator = PassValidator(
            registry=self.registry,
            strict_route_validation=True,
            strict_date_validation=True,
        )
        
        self.data_quality = DataQualityService(
            duplicate_window_seconds=self.config.passenger_duplicate_window_seconds,
            abnormal_submission_window_seconds=self.config.passenger_abnormal_submission_window_seconds,
            abnormal_submission_threshold=self.config.passenger_abnormal_submission_threshold,
            bus_capacity=self.bus_capacity,
        )
        
        self.boarding_service = BoardingService(
            validator=self.validator,
            data_quality=self.data_quality,
        )
        
        self.mock_ticketing = MockTicketingProvider()
        self._local_buffered_events: List[BoardingEvent] = []

    def get_current_gps(self) -> GPS:
        """Fetches active location from SharedGPSService or defaults gracefully"""
        if self.gps_service:
            fix = self.gps_service.get_latest_fix()
            if fix.valid:
                return GPS(
                    latitude=float(fix.latitude),
                    longitude=float(fix.longitude),
                    accuracy_m=float(fix.accuracy_m),
                )
        return GPS(latitude=12.9716, longitude=77.5946, accuracy_m=10.0)

    def record_pass_entry(
        self,
        pass_id: str,
        route_id: Optional[str] = None,
        stop_id: str = "STOP-GENERIC",
    ) -> Alert:
        """
        Invoked when a conductor enters a physical bus-pass number into the onboard terminal.
        """
        active_route = route_id or self.default_route_id
        gps = self.get_current_gps()

        event = self.boarding_service.process_pass_entry(
            pass_id=pass_id,
            bus_id=self.bus_id,
            route_id=active_route,
            stop_id=stop_id,
            latitude=gps.latitude,
            longitude=gps.longitude,
            timestamp=datetime.now(),
        )
        self._local_buffered_events.append(event)
        return self._convert_to_alert(event, gps)

    def record_ticket_entry(
        self,
        ticket_id: Optional[str] = None,
        route_id: Optional[str] = None,
        stop_id: str = "STOP-GENERIC",
    ) -> Alert:
        """
        Invoked when a normal ticket is purchased/issued on the onboard ETM.
        """
        active_route = route_id or self.default_route_id
        gps = self.get_current_gps()

        if not ticket_id:
            event = self.mock_ticketing.generate_ticket_event(
                bus_id=self.bus_id,
                route_id=active_route,
                stop_id=stop_id,
                lat=gps.latitude,
                lng=gps.longitude,
            )
        else:
            event = self.boarding_service.process_ticket_entry(
                ticket_id=ticket_id,
                bus_id=self.bus_id,
                route_id=active_route,
                stop_id=stop_id,
                latitude=gps.latitude,
                longitude=gps.longitude,
                timestamp=datetime.now(),
            )

        self._local_buffered_events.append(event)
        return self._convert_to_alert(event, gps)

    def _convert_to_alert(self, event: BoardingEvent, gps: GPS) -> Alert:
        """
        Maps a domain BoardingEvent into the unified edge Alert schema for offline SQLite queuing.
        """
        severity_map = {
            "valid": "low",
            "suspicious": "medium",
            "invalid": "low",
        }
        severity = severity_map.get(event.validation_status, "low")

        return Alert(
            alert_id=event.event_id,
            bus_id=event.bus_id,
            timestamp=event.timestamp,
            gps=gps,
            module=ModuleInfo(
                type="passenger_demand",
                version="1.0"
            ),
            severity=severity,
            payload=event.model_dump(mode="json"),
            source=SourceInfo(
                device_id=self.config.device_id if hasattr(self.config, "device_id") else "EDGE-01",
                camera_id="CONDUCTOR_ETM",
            ),
            evidence=None, # Module 4 has NO cameras
        )

    def get_buffered_events(self) -> List[BoardingEvent]:
        return list(self._local_buffered_events)
