from typing import List, Dict, Any, Optional
import math
from shared.config import Config
from shared.gps.gps_service import SharedGPSService
from shared.gps.gps_fix import GPSFix


class TrafficDensityAggregator:
    """
    Aggregates frame-by-frame vehicle counts over a rolling window/interval
    and classifies into LOW, MEDIUM, or HIGH traffic density with normalized intensities,
    associating real coordinates from SharedGPSService.
    """

    def __init__(
        self,
        fps: float = 30.0,
        interval_seconds: float = 2.0,
        low_threshold: Optional[int] = None,
        high_threshold: Optional[int] = None,
        gps_service: Optional[SharedGPSService] = None,
    ):
        config = Config()
        self.fps = fps if fps > 0 else 30.0
        self.interval_seconds = interval_seconds if interval_seconds > 0 else float(config.traffic_observation_interval)
        self.frames_per_interval = max(1, int(self.fps * self.interval_seconds))

        # Configurable thresholds
        self.low_threshold = (
            low_threshold
            if low_threshold is not None
            else int(config.get("module2_traffic", "traffic", "low_threshold", default=5))
        )
        self.high_threshold = (
            high_threshold
            if high_threshold is not None
            else int(config.get("module2_traffic", "traffic", "high_threshold", default=15))
        )

        self.gps_service = gps_service or SharedGPSService.get_instance(config=config)

        # Buffer for current interval
        self._current_counts: List[int] = []
        self._last_frame_number = 0

    def add_frame(self, frame_number: int, active_vehicle_count: int) -> Optional[Dict[str, Any]]:
        """
        Record an active vehicle count for a frame.
        Returns aggregated sample dict when interval completes, otherwise None.
        """
        self._current_counts.append(active_vehicle_count)
        self._last_frame_number = frame_number

        if len(self._current_counts) >= self.frames_per_interval:
            return self._finalize_sample()

        return None

    def flush(self) -> Optional[Dict[str, Any]]:
        """Flush remaining buffered frames if any."""
        if self._current_counts:
            return self._finalize_sample()
        return None

    def _finalize_sample(self) -> Dict[str, Any]:
        # Average vehicle count over the interval window
        avg_count = sum(self._current_counts) / max(1, len(self._current_counts))
        rounded_count = int(round(avg_count))

        # Classification and normalized heat intensity
        # LOW -> ~0.25, MEDIUM -> ~0.60, HIGH -> 1.00
        if avg_count <= self.low_threshold:
            traffic_level = "low"
            intensity = 0.25
        elif avg_count <= self.high_threshold:
            traffic_level = "medium"
            intensity = 0.60
        else:
            traffic_level = "high"
            intensity = 1.00

        timestamp_sec = round(self._last_frame_number / self.fps, 2)

        # Query latest location from SharedGPSService
        gps_fix: GPSFix = self.gps_service.get_latest_fix()
        lat = gps_fix.latitude if (gps_fix.valid and gps_fix.latitude is not None) else 12.9716
        lng = gps_fix.longitude if (gps_fix.valid and gps_fix.longitude is not None) else 77.5946

        sample = {
            "module_type": "traffic",
            "timestamp": timestamp_sec,
            "frame_number": self._last_frame_number,
            "vehicle_count": rounded_count,
            "traffic_level": traffic_level,
            "intensity": intensity,
            "latitude": float(lat),
            "longitude": float(lng),
            "source": gps_fix.source,
            "gps_valid": gps_fix.valid,
        }

        self._current_counts = []
        return sample
