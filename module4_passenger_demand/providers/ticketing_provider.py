import uuid
import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

from module4_passenger_demand.models.passenger_models import BoardingEvent


class TicketingDataProvider(ABC):
    """
    Abstract interface for physical conductor ETMs or ticketing system transactions.
    """
    @abstractmethod
    def generate_ticket_event(self, bus_id: str, route_id: str, stop_id: str) -> BoardingEvent:
        pass


class MockTicketingProvider(TicketingDataProvider):
    """
    Simulates standard cash/QR ticket purchases generated from an onboard Conductor ETM.
    Clearly marked as MOCK DATA for development/testing until physical hardware is interfaced.
    """
    def __init__(self):
        self.ticket_counter = 1000

    def generate_ticket_event(
        self,
        bus_id: str = "BUS-102",
        route_id: str = "25A",
        stop_id: str = "STOP-12",
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> BoardingEvent:
        self.ticket_counter += 1
        ticket_id = f"TKT-{self.ticket_counter}-{random.randint(100, 999)}"
        event_id = f"tkt_ev_{uuid.uuid4().hex[:10]}"

        return BoardingEvent(
            event_id=event_id,
            bus_id=bus_id,
            route_id=route_id,
            timestamp=datetime.now(),
            boarding_stop_id=stop_id,
            latitude=lat,
            longitude=lng,
            passenger_type="ticket",
            ticket_id=ticket_id,
            validation_status="valid",
            source="mock_etm_stream (MOCK DATA)",
            confidence=1.0,
        )
