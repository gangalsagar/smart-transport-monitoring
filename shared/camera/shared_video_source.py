from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timezone
import cv2
import numpy as np

from shared.camera.frame_packet import FramePacket


class SharedVideoSource:
    """
    Unified camera/video capture provider.
    
    Responsibilities:
    1. Opens the physical camera (DirectShow/default) or video file EXACTLY ONCE with a single cv2.VideoCapture.
    2. Decodes each frame once.
    3. Bundles the frame with sequential frame_number, playback time, and UTC timestamp into FramePacket.
    4. Releases the hardware/file resources cleanly on completion or error.
    """

    def __init__(self, source_path_or_index: str | int | Path):
        """
        :param source_path_or_index: File path (str/Path) or Camera device index (int, e.g. 1).
        """
        self.source = source_path_or_index
        self.capture: Optional[cv2.VideoCapture] = None
        self._frame_count = 0
        self._fps = 30.0
        self._width = 0
        self._height = 0
        self._total_frames = -1
        self._is_live_camera = False

    def open(self) -> bool:
        """Open the video stream or live camera device."""
        # Determine if integer camera index or string representation of an int
        is_int_index = False
        camera_idx = 0

        if isinstance(self.source, int):
            is_int_index = True
            camera_idx = self.source
        elif isinstance(self.source, str) and self.source.strip().isdigit():
            is_int_index = True
            camera_idx = int(self.source.strip())

        if is_int_index:
            self._is_live_camera = True
            # Try DirectShow first on Windows
            try:
                self.capture = cv2.VideoCapture(camera_idx, cv2.CAP_DSHOW)
            except Exception:
                self.capture = None

            if self.capture is None or not self.capture.isOpened():
                # Fallback to default backend
                self.capture = cv2.VideoCapture(camera_idx)

            if not self.capture.isOpened():
                raise RuntimeError(
                    f"ERROR: Could not open configured live camera.\n"
                    f"Camera Index: {camera_idx}\n"
                    f"Configured Source: live"
                )
        else:
            self._is_live_camera = False
            p = Path(self.source)
            if not p.exists():
                raise FileNotFoundError(f"Video file not found: {p}")
            self.capture = cv2.VideoCapture(str(p))

            if not self.capture.isOpened():
                raise RuntimeError(f"Could not open shared video file: {self.source}")

        fps_val = self.capture.get(cv2.CAP_PROP_FPS)
        self._fps = float(fps_val) if (fps_val and fps_val > 0) else 30.0
        self._width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if self._is_live_camera:
            self._total_frames = -1
        else:
            self._total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))

        self._frame_count = 0
        return True

    def read_packet(self) -> Optional[FramePacket]:
        """
        Read the next frame from the single video capture and return a FramePacket.
        Returns None at end-of-stream or on frame read error.
        """
        if self.capture is None or not self.capture.isOpened():
            return None

        success, frame = self.capture.read()
        if not success or frame is None:
            return None

        self._frame_count += 1
        video_time_seconds = round(float(self._frame_count) / self._fps, 3)

        return FramePacket(
            frame=frame,
            frame_number=self._frame_count,
            timestamp=datetime.now(timezone.utc),
            video_time_seconds=video_time_seconds,
            metadata={"source": str(self.source), "is_live": self._is_live_camera},
        )

    def release(self) -> None:
        """Release underlying cv2.VideoCapture resource."""
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def resolution(self) -> Tuple[int, int]:
        return self._width, self._height

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def current_frame_number(self) -> int:
        return self._frame_count

    @property
    def is_live_camera(self) -> bool:
        return self._is_live_camera

    def is_opened(self) -> bool:
        return self.capture is not None and self.capture.isOpened()
