from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np


class BaseIncidentModel(ABC):
    """
    Abstract contract for future Incident & Rash-Driving AI inference models.
    All models (placeholder, rule-based, or future trained PyTorch/ONNX/TensorRT)
    must implement this interface.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier name of the model (e.g. 'rash_driving_lstm_v1', 'accident_yolo_v8')."""
        pass

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        """Returns True if running a trained AI model weights file, False if placeholder/heuristic."""
        pass

    @abstractmethod
    def initialize(self, **kwargs) -> bool:
        """Load weights, configure hardware acceleration (CPU/GPU/TPU/NPU), and warm up."""
        pass

    @abstractmethod
    def infer(self, input_data: Any) -> List[Dict[str, Any]]:
        """
        Execute inference.
        
        Args:
            input_data: Can be a single frame (np.ndarray), frame sequence, or vehicle tracking history.
            
        Returns:
            List of candidate event predictions conforming to the model output contract.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return model metadata (architecture, input shape, version, device, parameters)."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Release GPU memory, inference sessions, and handles cleanly."""
        pass
