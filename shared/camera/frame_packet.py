from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any
import numpy as np


@dataclass
class FramePacket:
    """
    Shared frame data structure distributed to all edge vision modules.
    
    Attributes:
        frame (np.ndarray): Decoded video frame image (BGR format).
        frame_number (int): 1-indexed sequential frame number.
        timestamp (datetime): Timestamp corresponding to the frame capture.
        video_time_seconds (float): Video playback time in seconds (frame_number / fps).
        metadata (dict): Optional extra information for future GPS/telemetry integration.
    """
    frame: np.ndarray
    frame_number: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    video_time_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)
