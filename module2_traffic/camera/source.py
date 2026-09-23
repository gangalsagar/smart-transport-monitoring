from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np


class VideoSource(ABC):
    """
    Abstract Video/Camera source interface.
    Allows seamless switching between test video files, RTSP streams,
    and future camera hardware without modifying vision processing code.
    """

    @abstractmethod
    def open(self) -> bool:
        """Open the video stream or file."""
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read the next frame."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release the source resources."""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """Return FPS of the source."""
        pass

    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Return (width, height) of the stream."""
        pass

    @abstractmethod
    def get_total_frames(self) -> int:
        """Return total frames if available (or -1 for live stream)."""
        pass


class FileVideoSource(VideoSource):
    """
    Video file source implementation for testing and development.
    """

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.capture: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.file_path}")
        self.capture = cv2.VideoCapture(str(self.file_path))
        return self.capture.isOpened()

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.capture is None or not self.capture.isOpened():
            return False, None
        return self.capture.read()

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def get_fps(self) -> float:
        if self.capture is None:
            return 30.0
        fps = self.capture.get(cv2.CAP_PROP_FPS)
        return fps if fps > 0 else 30.0

    def get_resolution(self) -> Tuple[int, int]:
        if self.capture is None:
            return 0, 0
        w = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return w, h

    def get_total_frames(self) -> int:
        if self.capture is None:
            return -1
        return int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
