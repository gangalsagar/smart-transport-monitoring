from typing import Dict, Optional, Tuple


class IncidentConfirmationState:
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    CONFIRMED_INCIDENT = "CONFIRMED_INCIDENT"
    ANPR_PROCESSING = "ANPR_PROCESSING"
    REPORTED = "REPORTED"


class EventConfirmationManager:
    """
    Manages temporal confirmation, state machine progression, deduplication,
    and cooldowns for Module 3 events to prevent false positives and alert storms.
    """

    def __init__(
        self,
        rash_min_hits: int = 3,
        accident_min_hits: int = 2,
        cooldown_seconds: float = 15.0,
    ):
        self.rash_min_hits = rash_min_hits
        self.accident_min_hits = accident_min_hits
        self.cooldown_seconds = cooldown_seconds

        # Track candidate hit counters: (event_type, track_id) -> hit_count
        self._candidate_hits: Dict[Tuple[str, Optional[int]], int] = {}
        # Track last confirmed alert time: (event_type, track_id) -> timestamp_sec
        self._last_alert_time: Dict[Tuple[str, Optional[int]], float] = {}
        # Track state machine: (event_type, track_id) -> state string
        self._states: Dict[Tuple[str, Optional[int]], str] = {}

    def get_event_state(self, event_type: str, track_id: Optional[int]) -> str:
        key = (event_type, track_id)
        return self._states.get(key, IncidentConfirmationState.NORMAL)

    def should_confirm_event(
        self,
        event_type: str,
        track_id: Optional[int],
        confidence: float,
        video_time_seconds: float,
    ) -> bool:
        """
        Evaluate if a candidate prediction satisfies consecutive detection count
        and is outside the deduplication cooldown window.
        """
        key = (event_type, track_id)

        # Check cooldown
        if key in self._last_alert_time:
            last_time = self._last_alert_time[key]
            if (video_time_seconds - last_time) < self.cooldown_seconds:
                return False

        # Accumulate hit
        hits = self._candidate_hits.get(key, 0) + 1
        self._candidate_hits[key] = hits

        min_hits = self.accident_min_hits if event_type in {"accident", "collision"} else self.rash_min_hits

        if hits < min_hits:
            self._states[key] = IncidentConfirmationState.SUSPICIOUS
            return False

        # Confirmed
        self._states[key] = IncidentConfirmationState.CONFIRMED_INCIDENT
        self._last_alert_time[key] = video_time_seconds
        self._candidate_hits[key] = 0
        return True

    def mark_reported(self, event_type: str, track_id: Optional[int]) -> None:
        key = (event_type, track_id)
        self._states[key] = IncidentConfirmationState.REPORTED
