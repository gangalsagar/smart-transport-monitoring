import sys
import argparse
import time
import cv2

from shared.camera.shared_video_source import SharedVideoSource
from shared.config import Config


def test_camera(
    source_type: str = "live",
    camera_index: int = 1,
    preview: bool = False,
    max_frames: int = 50,
):
    print("=" * 60)
    print("SHARED CAMERA SERVICE TEST")
    print("=" * 60)

    config = Config()

    if source_type == "live":
        source = camera_index
        print(f"Mode         : LIVE CAMERA (Connected Mobile Camera)")
        print(f"Camera Index : {source}")
    else:
        source = config.resolve_path(config.combined_input_video)
        print(f"Mode         : FILE VIDEO")
        print(f"File Path    : {source}")

    video_source = SharedVideoSource(source)

    try:
        print("\nOpening camera source...")
        video_source.open()
        width, height = video_source.resolution
        fps = video_source.fps
        print(f"[OK] Camera opened successfully.")
        print(f"Resolution : {width}x{height}")
        print(f"FPS        : {fps:.1f}")
        print(f"Total      : {'LIVE STREAM' if video_source.is_live_camera else f'{video_source.total_frames} frames'}")

        print(f"\nReading test frames (preview={preview})...")
        if preview:
            print("Press 'q' in the preview window to stop early.")

        frames_read = 0
        start_time = time.time()

        while True:
            packet = video_source.read_packet()
            if packet is None:
                print("End of stream or no frame received.")
                break

            frames_read += 1
            if frames_read % 10 == 0 or frames_read == 1:
                print(f"  Frame {frames_read:03d} read: shape={packet.frame.shape}, time={packet.video_time_seconds:.2f}s")

            if preview:
                cv2.imshow("Shared Camera Service Test", packet.frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("User requested exit from preview window.")
                    break

            if not preview and frames_read >= max_frames:
                break

        elapsed = time.time() - start_time
        fps_measured = frames_read / elapsed if elapsed > 0 else 0.0

        print("-" * 60)
        print(f"Test Successful: {frames_read} frames read in {elapsed:.2f}s ({fps_measured:.1f} FPS)")

    except Exception as e:
        print(f"\n[ERROR] Camera test failed: {e}")
        return False
    finally:
        video_source.release()
        if preview:
            cv2.destroyAllWindows()
        print("Camera released cleanly.")
        print("=" * 60)

    return True


def main():
    parser = argparse.ArgumentParser(description="Standalone Shared Camera Service Test")
    parser.add_argument("--source", choices=["live", "file"], default="live", help="Camera source mode")
    parser.add_argument("--index", type=int, default=1, help="Live camera index (default: 1 for connected mobile camera)")
    parser.add_argument("--preview", action="store_true", help="Display live OpenCV preview window")
    parser.add_argument("--frames", type=int, default=30, help="Number of frames to read in non-preview mode")

    args = parser.parse_args()
    success = test_camera(
        source_type=args.source,
        camera_index=args.index,
        preview=args.preview,
        max_frames=args.frames,
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
