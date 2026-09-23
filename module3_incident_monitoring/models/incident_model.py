from typing import Any, Dict, List, Optional
from pathlib import Path
import numpy as np

from module3_incident_monitoring.models.base_model import BaseIncidentModel


class IncidentDetectionModel(BaseIncidentModel):
    """
    Model interface & pre-training implementation for Accidents, Collisions, and Emergencies.
    Supports future trained computer vision models (e.g. YOLO-Accident, ViT-Incident, I3D).
    """

    def __init__(
        self,
        weights_path: Optional[str | Path] = None,
        confidence_threshold: float = 0.70,
        device: str = "cpu",
    ):
        self.weights_path = Path(weights_path) if weights_path else None
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._is_initialized = False
        self._has_trained_weights = False

    @property
    def model_name(self) -> str:
        return "incident_accident_detector_v1"

    @property
    def is_trained(self) -> bool:
        return self._has_trained_weights

    def initialize(self, **kwargs) -> bool:
        """
        Check for trained weights. If weights are found, load model;
        otherwise initialize in pre-training placeholder mode.
        """
        if self.weights_path and self.weights_path.exists() and self.weights_path.is_file():
            self._has_trained_weights = True
        else:
            self._has_trained_weights = False

        self._is_initialized = True
        return True

    def infer(self, input_data: Any) -> List[Dict[str, Any]]:
        """
        Infer accidents or collisions from incoming frame or frame sequences.
        
        Input contract:
            input_data can be:
            1. np.ndarray: Raw BGR frame image
            2. List[np.ndarray]: Temporal sequence of frames (e.g., 8-16 frames)
            3. Dict with tracking/overlap data:
               {
                   'frame': np.ndarray,
                   'overlapping_tracks': [(track_a, track_b, iou), ...],
                   'stationary_vehicles': [track_id, ...],
               }
            
        Output contract:
            Returns a list of candidate prediction dictionaries:
            [
                {
                    'detected': bool,
                    'event_type': 'accident' | 'collision' | 'vehicle_breakdown' | 'emergency_obstacle',
                    'confidence': float,
                    'track_id': Optional[int],
                    'bbox': Optional[List[int]],
                    'details': dict,
                }
            ]
        """
        if not self._is_initialized:
            self.initialize()

        if self._has_trained_weights:
            # Future inference pipeline
            return []

        # Placeholder heuristic for testing pipeline flow
        if isinstance(input_data, dict):
            overlaps = input_data.get("overlapping_tracks", [])
            predictions = []
            for track_a, track_b, iou in overlaps:
                if iou > 0.65:
                    predictions.append({
                        "detected": True,
                        "event_type": "collision",
                        "confidence": 0.85,
                        "track_id": track_a,
                        "details": {"colliding_tracks": [track_a, track_b], "overlap_iou": round(iou, 2)},
                    })
            return predictions

        return []

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "is_trained": self.is_trained,
            "weights_path": str(self.weights_path) if self.weights_path else None,
            "confidence_threshold": self.confidence_threshold,
            "device": self.device,
            "supported_events": [
                "accident",
                "collision",
                "vehicle_breakdown",
                "emergency_obstacle",
                "unknown_incident",
            ],
        }

    def shutdown(self) -> None:
        self._is_initialized = False
