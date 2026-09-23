from pathlib import Path
from typing import Optional, Dict, Any
from shared.config import Config


class Module3Config:
    """Configuration loader for Module 3 Incident Monitoring."""

    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config()

    @property
    def enabled(self) -> bool:
        return bool(self._config.get("module3_incident_monitoring", "enabled", default=True))

    @property
    def accident_detection_enabled(self) -> bool:
        return bool(self._config.get("module3_incident_monitoring", "accident_detection_enabled", default=True))

    @property
    def rash_driving_detection_enabled(self) -> bool:
        return bool(self._config.get("module3_incident_monitoring", "rash_driving_detection_enabled", default=False))

    @property
    def anpr_on_confirmed_incident_only(self) -> bool:
        return bool(self._config.get("module3_incident_monitoring", "anpr_on_confirmed_incident_only", default=True))

    @property
    def pre_incident_seconds(self) -> float:
        return float(self._config.get("module3_incident_monitoring", "evidence", "pre_incident_seconds", default=3.0))

    @property
    def post_incident_seconds(self) -> float:
        return float(self._config.get("module3_incident_monitoring", "evidence", "post_incident_seconds", default=3.0))

    @property
    def max_buffer_frames(self) -> int:
        return int(self._config.get("module3_incident_monitoring", "evidence", "max_buffer_frames", default=45))

    @property
    def rash_model_weights(self) -> Optional[Path]:
        path_str = self._config.get("module3_incident_monitoring", "models", "rash_driving", "weights", default="")
        if path_str:
            return self._config.resolve_path(path_str)
        return None

    @property
    def accident_model_weights(self) -> Optional[Path]:
        path_str = self._config.get("module3_incident_monitoring", "models", "accident", "weights", default="")
        if path_str:
            return self._config.resolve_path(path_str)
        return None

    @property
    def confidence_threshold(self) -> float:
        return float(self._config.get("module3_incident_monitoring", "confidence_threshold", default=0.65))

    @property
    def plate_recognition_enabled(self) -> bool:
        return bool(self._config.get("module3_incident_monitoring", "anpr", "enabled", default=True))

    @property
    def emergency_immediate_dispatch(self) -> bool:
        return bool(self._config.get("module3_incident_monitoring", "emergency", "immediate_dispatch", default=True))

    @property
    def evidence_directory(self) -> Path:
        return self._config.resolve_path("module3_incident_monitoring/data/evidence")
