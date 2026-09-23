from collections import deque
from typing import List, Optional, Tuple, Dict, Any
import numpy as np


class RollingFrameBuffer:
    """
    Bounded in-memory ring buffer of recent video frames and timestamps.
    Provides temporal context window around confirmed incidents for temporal OCR consensus.
    """

    def __init__(self, max_frames: int = 30):
        self.max_frames = max(5, max_frames)
        # Stores (frame_number, timestamp_sec, np.ndarray frame, tracked_vehicles_snapshot)
        self._buffer: deque = deque(maxlen=self.max_frames)

    def add_frame(
        self,
        frame_number: int,
        timestamp_sec: float,
        frame: np.ndarray,
        tracked_vehicles: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Append frame to bounded circular buffer."""
        # Store a copy or reference depending on memory
        self._buffer.append((frame_number, timestamp_sec, frame.copy(), tracked_vehicles or []))

    def get_window_frames(
        self,
        target_frame: int,
        pre_frames: int = 5,
        post_frames: int = 5,
    ) -> List[Tuple[int, float, np.ndarray, List[Dict[str, Any]]]]:
        """
        Extract frames within [target_frame - pre_frames, target_frame + post_frames].
        """
        min_f = target_frame - pre_frames
        max_f = target_frame + post_frames
        result = []
        for item in self._buffer:
            f_no = item[0]
            if min_f <= f_no <= max_f:
                result.append(item)
        return result

    def clear(self) -> None:
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)
