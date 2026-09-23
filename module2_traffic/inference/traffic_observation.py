from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

from module2_traffic.location.mock_gps import MockGPSRoute, GPSCoordinate
from shared.schemas.alert_schema import Alert, GPS, ModuleInfo, SourceInfo
from shared.config import Config
from shared.gps.gps_service import SharedGPSService
from shared.gps.gps_fix import GPSFix


class TrafficObservationCollector:
    """
    Collects traffic analysis every 10 seconds of video time (configurable)
    and constructs standard Alert objects with shared GPS coordinates
    and complete traffic metrics for dashboard heatmap rendering.
    """

    def __init__(
        self,
        fps: float = 25.0,
        interval_seconds: float = 10.0,
        gps_service: Optional[SharedGPSService] = None,
        mock_gps: Optional[MockGPSRoute] = None,
        config: Optional[Config] = None,
    ):
        self.config = config or Config()
        self.fps = fps if fps > 0 else 25.0
        self.interval_seconds = max(1.0, interval_seconds)
        self.interval_frames = max(1, int(self.fps * self.interval_seconds))

        self.gps_service = gps_service or SharedGPSService.get_instance(config=self.config)
        self.mock_gps = mock_gps  # Optional fallback if explicitly provided
        self.observations: List[Alert] = []
        self._last_observation_frame = 0

    def check_and_generate(
        self,
        frame_number: int,
        analysis: Dict[str, Any],
        counting_summary: Dict[str, Any],
        is_final: bool = False,
    ) -> Optional[Alert]:
        """
        Check if an interval of ~10 seconds has passed since the last observation,
        or if it's the final frame of the video.
        """
        frames_since_last = frame_number - self._last_observation_frame

        if frames_since_last >= self.interval_frames or (is_final and frames_since_last >= int(self.fps * 2.0)):
            alert = self._create_observation_alert(
                frame_number=frame_number,
                analysis=analysis,
                counting_summary=counting_summary,
            )
            self.observations.append(alert)
            self._last_observation_frame = frame_number
            return alert

        return None

    def _create_observation_alert(
        self,
        frame_number: int,
        analysis: Dict[str, Any],
        counting_summary: Dict[str, Any],
    ) -> Alert:
        """
        Create standard Alert schema object for a 10-second traffic observation.
        """
        # Read latest location from centralized SharedGPSService
        gps_fix: GPSFix = self.gps_service.get_latest_fix()

        if gps_fix.valid:
            latitude = float(gps_fix.latitude)
            longitude = float(gps_fix.longitude)
            accuracy_m = float(gps_fix.accuracy_m if gps_fix.accuracy_m > 0 else 5.0)
            source_label = gps_fix.source
        elif self.mock_gps is not None:
            # Fallback to mock GPS only if explicitly configured
            mock_coord: GPSCoordinate = self.mock_gps.get_next_position()
            latitude = mock_coord.latitude
            longitude = mock_coord.longitude
            accuracy_m = mock_coord.accuracy_m
            source_label = "mock_gps_route"
        else:
            # Safe default location fix
            latitude = 12.9716
            longitude = 77.5946
            accuracy_m = 5.0
            source_label = gps_fix.source

        # Extract congestion and severity
        congestion_level = str(analysis.get("congestion_level", "low")).lower()
        severity = str(analysis.get("severity", congestion_level)).lower()
        if severity not in {"low", "medium", "high", "critical"}:
            severity = "low"

        video_time_seconds = round(float(frame_number) / self.fps, 2)

        payload = {
            "frame_number": frame_number,
            "video_time_seconds": video_time_seconds,
            "traffic_observation": True,
            "congestion_level": congestion_level,
            "active_vehicle_count": int(analysis.get("active_vehicle_count", 0)),
            "total_vehicle_count": int(counting_summary.get("total_count", 0)),
            "occupancy_pct": float(analysis.get("occupancy_pct", 0.0)),
            "density": str(analysis.get("density", "low")),
            "severity": severity,
            "vehicle_classes": dict(counting_summary.get("class_counts", analysis.get("vehicle_classes", {}))),
            "directional_counts": dict(counting_summary.get("directional_counts", analysis.get("directional_counts", {}))),
            "gps_source": source_label,
            "gps_valid": gps_fix.valid,
            "gps_stale": gps_fix.stale,
            "gps_age_seconds": round(gps_fix.age_seconds, 2),
        }

        alert = Alert(
            alert_id=str(uuid4()),
            bus_id=str(getattr(self.config, "traffic_bus_id", "BUS-TEST")),
            timestamp=datetime.now(timezone.utc),
            gps=GPS(
                latitude=latitude,
                longitude=longitude,
                accuracy_m=accuracy_m,
            ),
            module=ModuleInfo(
                type="traffic",
                version="1.0",
            ),
            severity=severity,
            payload=payload,
            source=SourceInfo(
                device_id=str(getattr(self.config, "traffic_device_id", "EDGE-01")),
                camera_id=str(getattr(self.config, "traffic_camera_id", "FRONT_CAM")),
            ),
            evidence=None,
        )

        return alert
