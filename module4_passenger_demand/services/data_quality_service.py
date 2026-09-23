import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, Deque

from module4_passenger_demand.models.passenger_models import BoardingEvent

logger = logging.getLogger(__name__)


class DataQualityService:
    """
    Guards against conductor data-entry mistakes, rapid miscounts, and duplicate submissions.
    
    Principles:
    - Never blindly trust manual entries.
    - Never automatically accuse the conductor of fraud.
    - Classify suspicious anomalies with audit reasons (abnormal_submission_rate, duplicate_submission, capacity_exceeded).
    - Retain all records for transparency; do not delete suspicious events.
    """
    def __init__(
        self,
        duplicate_window_seconds: float = 15.0,
        abnormal_submission_window_seconds: float = 20.0,
        abnormal_submission_threshold: int = 8,
        bus_capacity: int = 60,
    ):
        self.duplicate_window = timedelta(seconds=duplicate_window_seconds)
        self.burst_window = timedelta(seconds=abnormal_submission_window_seconds)
        self.burst_threshold = abnormal_submission_threshold
        self.bus_capacity = bus_capacity

        # Tracks recent submissions for duplicate detection: (pass_id, bus_id, route_id) -> timestamp
        self._recent_pass_submissions: Dict[Tuple[str, str, str], datetime] = {}
        
        # Sliding window of recent submission timestamps per conductor/terminal: bus_id -> deque([timestamps])
        self._submission_timestamps: Dict[str, Deque[datetime]] = {}

        # Trip-level cumulative count tracker: (bus_id, route_id) -> int
        self._trip_boardings_count: Dict[Tuple[str, str], int] = {}

    def audit_boarding_event(self, event: BoardingEvent) -> BoardingEvent:
        now = event.timestamp or datetime.now()
        bus_id = event.bus_id
        route_id = event.route_id

        # 1. Abnormal submission rate (rapid conductor entry burst)
        if bus_id not in self._submission_timestamps:
            self._submission_timestamps[bus_id] = deque()
        timestamps = self._submission_timestamps[bus_id]
        
        # Clean older timestamps
        while timestamps and (now - timestamps[0]) > self.burst_window:
            timestamps.popleft()
        
        timestamps.append(now)
        if len(timestamps) > self.burst_threshold:
            event.validation_status = "suspicious"
            event.validation_reason = "abnormal_submission_rate"
            return event

        # 2. Duplicate submission check (same pass re-entered in seconds on same bus/trip)
        if event.passenger_type == "pass" and event.pass_id:
            pass_key = (event.pass_id.upper(), bus_id, route_id)
            last_seen = self._recent_pass_submissions.get(pass_key)
            if last_seen and (now - last_seen) < self.duplicate_window:
                event.validation_status = "suspicious"
                event.validation_reason = "possible_duplicate_submission"
                return event
            self._recent_pass_submissions[pass_key] = now

        # 3. Capacity exceeded check
        trip_key = (bus_id, route_id)
        current_boardings = self._trip_boardings_count.get(trip_key, 0) + 1
        self._trip_boardings_count[trip_key] = current_boardings

        # If boardings drastically exceed physical bus capacity (e.g. > 180% of capacity)
        if self.bus_capacity > 0 and current_boardings > (self.bus_capacity * 1.8):
            event.validation_status = "suspicious"
            event.validation_reason = "capacity_exceeded"
            return event

        return event

    def reset_trip_count(self, bus_id: str, route_id: str):
        self._trip_boardings_count[(bus_id, route_id)] = 0
