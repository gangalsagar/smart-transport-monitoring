import time
from pathlib import Path

import cv2


class CameraSource:
    """
    Common interface for all edge camera sources.

    The AI pipeline should only depend on this interface.

    Implementations:
        - VideoFileSource
        - OpenCVCameraSource
    """

    def open(self):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError

    @property
    def fps(self):
        return 30.0

    @property
    def width(self):
        return 0

    @property
    def height(self):
        return 0


class VideoFileSource(CameraSource):
    """
    CameraSource implementation backed by a video file.

    Used for development/testing.
    """

    def __init__(self, video_path):

        self.video_path = Path(
            video_path
        )

        self.capture = None

        self._fps = 30.0
        self._width = 0
        self._height = 0

    def open(self):

        if not self.video_path.exists():

            raise FileNotFoundError(
                f"Video not found:\n"
                f"{self.video_path}"
            )

        self.capture = cv2.VideoCapture(
            str(self.video_path)
        )

        if not self.capture.isOpened():

            raise RuntimeError(
                f"Could not open video:\n"
                f"{self.video_path}"
            )

        self._fps = (
            self.capture.get(
                cv2.CAP_PROP_FPS
            )
        )

        if self._fps <= 0:

            self._fps = 30.0

        self._width = int(
            self.capture.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        self._height = int(
            self.capture.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        return self

    def read(self):

        if self.capture is None:

            raise RuntimeError(
                "VideoFileSource is not open."
            )

        success, frame = (
            self.capture.read()
        )

        return success, frame

    def release(self):

        if self.capture is not None:

            self.capture.release()

            self.capture = None

    @property
    def fps(self):

        return self._fps

    @property
    def width(self):

        return self._width

    @property
    def height(self):

        return self._height


class OpenCVCameraSource(CameraSource):
    """
    Physical camera source using OpenCV.

    Typical edge-device usage:

        OpenCVCameraSource(camera_index=0)

    On Windows this can correspond to the integrated
    webcam or a USB camera.

    On Linux edge hardware, the camera index can point
    to a V4L2 device such as /dev/video0.
    """

    def __init__(
        self,
        camera_index=0,
        width=1280,
        height=720,
        fps=30,
        backend=None,
        warmup_seconds=2.0,
    ):

        self.camera_index = camera_index

        self.requested_width = width
        self.requested_height = height
        self.requested_fps = fps

        self.backend = backend

        self.warmup_seconds = (
            warmup_seconds
        )

        self.capture = None

        self._fps = float(fps)
        self._width = width
        self._height = height

    def open(self):

        # ----------------------------------------------------
        # Open camera
        # ----------------------------------------------------

        if self.backend is None:

            self.capture = (
                cv2.VideoCapture(
                    self.camera_index
                )
            )

        else:

            self.capture = (
                cv2.VideoCapture(
                    self.camera_index,
                    self.backend
                )
            )

        if not self.capture.isOpened():

            raise RuntimeError(
                "Could not open camera "
                f"index {self.camera_index}."
            )

        # ----------------------------------------------------
        # Request camera properties
        # ----------------------------------------------------

        self.capture.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.requested_width
        )

        self.capture.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.requested_height
        )

        self.capture.set(
            cv2.CAP_PROP_FPS,
            self.requested_fps
        )

        # ----------------------------------------------------
        # Read actual properties
        # ----------------------------------------------------

        actual_width = int(
            self.capture.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        actual_height = int(
            self.capture.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        actual_fps = (
            self.capture.get(
                cv2.CAP_PROP_FPS
            )
        )

        if actual_width > 0:

            self._width = actual_width

        if actual_height > 0:

            self._height = actual_height

        if actual_fps > 0:

            self._fps = actual_fps

        # ----------------------------------------------------
        # Camera warmup
        # ----------------------------------------------------

        if self.warmup_seconds > 0:

            time.sleep(
                self.warmup_seconds
            )

        return self

    def read(self):

        if self.capture is None:

            raise RuntimeError(
                "OpenCVCameraSource is not open."
            )

        return self.capture.read()

    def release(self):

        if self.capture is not None:

            self.capture.release()

            self.capture = None

    @property
    def fps(self):

        return self._fps

    @property
    def width(self):

        return self._width

    @property
    def height(self):

        return self._height


def test_video_source():

    print("=" * 60)
    print("VIDEO FILE CAMERA SOURCE TEST")
    print("=" * 60)

    project_root = (
        Path(__file__).resolve().parents[2]
    )

    video_path = (
        project_root
        / "module1_road_defect"
        / "data"
        / "videos"
        / "test_video.mp4"
    )

    source = VideoFileSource(
        video_path
    )

    source.open()

    print(
        f"\nSource:"
    )

    print(
        source.video_path
    )

    print(
        f"\nFPS: "
        f"{source.fps:.2f}"
    )

    print(
        f"Resolution: "
        f"{source.width}x{source.height}"
    )

    frames = 0

    while frames < 5:

        success, frame = (
            source.read()
        )

        if not success:

            break

        frames += 1

        print(
            f"Frame {frames}: "
            f"{frame.shape}"
        )

    source.release()

    print(
        "\nVideo source test complete."
    )


def test_physical_camera():

    print("=" * 60)
    print("PHYSICAL CAMERA SOURCE TEST")
    print("=" * 60)

    source = OpenCVCameraSource(
        camera_index=0,
        width=1280,
        height=720,
        fps=30,
        warmup_seconds=1.0,
    )

    try:

        source.open()

        print(
            "\nCamera opened successfully."
        )

        print(
            f"Camera index: "
            f"{source.camera_index}"
        )

        print(
            f"FPS: "
            f"{source.fps:.2f}"
        )

        print(
            f"Resolution: "
            f"{source.width}x{source.height}"
        )

        print(
            "\nReading 10 frames..."
        )

        frames = 0

        while frames < 10:

            success, frame = (
                source.read()
            )

            if not success:

                print(
                    "Failed to read frame."
                )

                break

            frames += 1

            print(
                f"Frame {frames}: "
                f"{frame.shape}"
            )

        print(
            f"\nFrames successfully read: "
            f"{frames}"
        )

    finally:

        source.release()

    print(
        "\nPhysical camera test complete."
    )


def main():

    test_video_source()

    print()

    test_physical_camera()


if __name__ == "__main__":

    main()