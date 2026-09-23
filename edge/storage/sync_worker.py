import threading
import time

from edge.storage.alert_sync import AlertSync


class AlertSyncWorker:
    """
    Background synchronization worker for the edge device.

    The worker periodically checks the local SQLite queue and
    attempts to send pending/failed alerts to the central backend.

    The worker is independent from the AI processing loop.

    If the backend is unavailable:
        - AI processing continues
        - alerts remain in SQLite
        - the worker retries later
    """

    def __init__(
        self,
        backend_url="http://127.0.0.1:8001",
        interval_seconds=5,
        batch_size=20,
    ):

        self.sync = AlertSync(
            backend_url=backend_url
        )

        self.interval_seconds = (
            interval_seconds
        )

        self.batch_size = batch_size

        self._stop_event = (
            threading.Event()
        )

        self._thread = None

    # ========================================================
    # ONE SYNC CYCLE
    # ========================================================

    def run_once(self):

        try:

            summary = (
                self.sync.queue.summary()
            )

            pending = (
                summary["pending"]
            )

            failed = (
                summary["failed"]
            )

            if pending == 0 and failed == 0:

                return {
                    "attempted": 0,
                    "sent": 0,
                    "failed": 0,
                }

            if not self.sync.backend_available():

                print(
                    "\n[SYNC] Backend unavailable"
                )

                print(
                    "[SYNC] Alerts remain in local queue"
                )

                return {
                    "attempted": 0,
                    "sent": 0,
                    "failed": 0,
                    "backend_available": False,
                }

            result = self.sync.sync(
                limit=self.batch_size
            )

            print(
                "\n[SYNC] Synchronization:"
            )

            print(
                f"  Attempted : "
                f"{result['attempted']}"
            )

            print(
                f"  Sent      : "
                f"{result['sent']}"
            )

            print(
                f"  Failed    : "
                f"{result['failed']}"
            )

            return result

        except Exception as exc:

            print(
                f"\n[SYNC] Worker error: {exc}"
            )

            return {
                "attempted": 0,
                "sent": 0,
                "failed": 0,
                "error": str(exc),
            }

    # ========================================================
    # BACKGROUND LOOP
    # ========================================================

    def _worker_loop(self):

        print(
            "\n[SYNC] Background worker started"
        )

        print(
            f"[SYNC] Interval: "
            f"{self.interval_seconds} seconds"
        )

        while not self._stop_event.is_set():

            self.run_once()

            self._stop_event.wait(
                self.interval_seconds
            )

        print(
            "\n[SYNC] Background worker stopped"
        )

    # ========================================================
    # START
    # ========================================================

    def start(self):

        if (
            self._thread is not None
            and self._thread.is_alive()
        ):

            return

        self._stop_event.clear()

        self._thread = (
            threading.Thread(
                target=self._worker_loop,
                name="AlertSyncWorker",
                daemon=True,
            )
        )

        self._thread.start()

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self._stop_event.set()

        if (
            self._thread is not None
            and self._thread.is_alive()
        ):

            self._thread.join(
                timeout=2
            )

        self._thread = None
