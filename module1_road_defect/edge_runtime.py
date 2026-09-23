from pathlib import Path

from module1_road_defect.inference.video_processor import VideoProcessor
from module1_road_defect.storage.alert_queue import AlertQueue
from module1_road_defect.storage.alert_sync import AlertSync
from module1_road_defect.storage.sync_worker import AlertSyncWorker


class EdgeRuntime:
    """
    Main edge-AI runtime coordinator.

    Architecture:

        Camera / Video
              |
              v
        YOLO detection
              |
              v
           Tracker
              |
              v
             GPS
              |
              v
          Evidence
              |
              v
            Alert
              |
              v
        SQLite Queue
              |
              +----------------------+
              |                      |
              v                      v
        AI processing          Background Sync
                                     |
                                     v
                                Central Backend

    The AI pipeline and backend synchronization are independent.

    If the backend is unavailable:
        - AI processing continues
        - alerts are stored locally
        - sync worker retries later
    """

    def __init__(
        self,
        video_path=None,
        backend_url="http://127.0.0.1:8001",
        frame_skip=5,
        confidence=0.28,
        sync_interval=5,
        sync_batch_size=20,
    ):

        project_root = (
            Path(__file__).resolve().parents[1]
        )

        if video_path is None:

            video_path = (
                project_root
                / "module1_road_defect"
                / "data"
                / "videos"
                / "test_video.mp4"
            )

        self.video_path = Path(
            video_path
        )

        self.backend_url = (
            backend_url.rstrip("/")
        )

        self.frame_skip = frame_skip
        self.confidence = confidence

        # ----------------------------------------------------
        # Persistent edge queue
        # ----------------------------------------------------

        self.queue = AlertQueue()

        # ----------------------------------------------------
        # Synchronizer
        # ----------------------------------------------------

        self.sync = AlertSync(
            backend_url=self.backend_url,
            queue=self.queue,
        )

        # ----------------------------------------------------
        # Background synchronization worker
        # ----------------------------------------------------

        self.sync_worker = AlertSyncWorker(
            backend_url=self.backend_url,
            interval_seconds=sync_interval,
            batch_size=sync_batch_size,
        )

    # ========================================================
    # ONE-TIME SYNCHRONIZATION
    # ========================================================

    def synchronize(self):

        print("\n" + "=" * 60)
        print("EDGE QUEUE SYNCHRONIZATION")
        print("=" * 60)

        print(
            f"\nBackend:\n"
            f"{self.backend_url}"
        )

        print(
            "\nQueue before synchronization:"
        )

        print(
            self.queue.summary()
        )

        if not self.sync.backend_available():

            print(
                "\nBackend unavailable."
            )

            print(
                "Alerts remain safely in the local queue."
            )

            return {
                "attempted": 0,
                "sent": 0,
                "failed": 0,
                "backend_available": False,
            }

        result = self.sync.sync(
            limit=20
        )

        result[
            "backend_available"
        ] = True

        print(
            "\nSynchronization result:"
        )

        print(
            result
        )

        print(
            "\nQueue after synchronization:"
        )

        print(
            self.queue.summary()
        )

        return result

    # ========================================================
    # PROCESS VIDEO
    # ========================================================

    def process_video(self):

        if not self.video_path.exists():

            raise FileNotFoundError(
                f"Input video not found:\n"
                f"{self.video_path}"
            )

        print("\n" + "=" * 60)
        print("EDGE AI ROAD-DEFECT RUNTIME")
        print("=" * 60)

        print(
            f"\nInput:\n"
            f"{self.video_path}"
        )

        print(
            f"\nBackend:\n"
            f"{self.backend_url}"
        )

        print(
            "\nEdge queue:"
        )

        print(
            self.queue.database_path
        )

        processor = VideoProcessor(
            video_path=self.video_path,
            frame_skip=self.frame_skip,
            confidence=self.confidence,
            backend_url=self.backend_url,
        )

        print(
            "\nStarting vision pipeline..."
        )

        alerts = processor.process()

        # ----------------------------------------------------
        # Add alerts to persistent edge queue
        # ----------------------------------------------------

        queued = 0
        already_queued = 0

        print(
            "\nAdding generated alerts to edge queue..."
        )

        for alert in alerts:

            inserted = self.queue.enqueue(
                alert
            )

            if inserted:

                queued += 1

            else:

                already_queued += 1

        print(
            "\nQueue insertion:"
        )

        print(
            f"  New alerts      : {queued}"
        )

        print(
            f"  Already present : {already_queued}"
        )

        print(
            f"  Queue summary   : "
            f"{self.queue.summary()}"
        )

        return alerts

    # ========================================================
    # START BACKGROUND SYNC
    # ========================================================

    def start_sync_worker(self):

        print(
            "\nStarting background alert synchronization..."
        )

        self.sync_worker.start()

        print(
            "Background synchronization enabled."
        )

    # ========================================================
    # STOP BACKGROUND SYNC
    # ========================================================

    def stop_sync_worker(self):

        print(
            "\nStopping background alert synchronization..."
        )

        self.sync_worker.stop()

        print(
            "Background synchronization stopped."
        )

    # ========================================================
    # COMPLETE RUNTIME
    # ========================================================

    def run(self):

        print("\n" + "=" * 60)
        print("SMART TRANSPORT EDGE RUNTIME")
        print("=" * 60)

        # ----------------------------------------------------
        # Stage 1
        # ----------------------------------------------------

        print(
            "\nStage 1: synchronize existing queued alerts"
        )

        self.synchronize()

        # ----------------------------------------------------
        # Stage 2
        # ----------------------------------------------------

        print(
            "\nStage 2: start background synchronization"
        )

        self.start_sync_worker()

        # ----------------------------------------------------
        # Stage 3
        # ----------------------------------------------------

        print(
            "\nStage 3: run road-defect vision pipeline"
        )

        alerts = []

        try:

            alerts = self.process_video()

        finally:

            # ------------------------------------------------
            # Give the worker a chance to synchronize the
            # newly generated alerts.
            # ------------------------------------------------

            print(
                "\nStage 4: final synchronization"
            )

            self.synchronize()

            self.stop_sync_worker()

        # ----------------------------------------------------
        # Final summary
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print("EDGE RUNTIME COMPLETE")
        print("=" * 60)

        print(
            f"\nAlerts generated : "
            f"{len(alerts)}"
        )

        print(
            f"Queue status     : "
            f"{self.queue.summary()}"
        )

        print(
            "\nEdge runtime finished successfully."
        )

        return alerts


def main():

    runtime = EdgeRuntime(
        backend_url="http://127.0.0.1:8001",
        frame_skip=5,
        confidence=0.28,
        sync_interval=5,
        sync_batch_size=20,
    )

    runtime.run()


if __name__ == "__main__":

    main()