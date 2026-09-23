from pathlib import Path

from typing import Any, List, Optional

from datetime import datetime, timezone

from uuid import uuid4


from module2_traffic.camera.source import (
    VideoSource,
    FileVideoSource,
)

from module2_traffic.inference.video_processor import (
    TrafficVideoProcessor,
)

from module1_road_defect.storage.alert_queue import (
    AlertQueue,
)

from module1_road_defect.storage.alert_sync import (
    AlertSync,
)

from module1_road_defect.storage.sync_worker import (
    AlertSyncWorker,
)

from shared.config import Config

from shared.schemas.alert_schema import (
    Alert,
    GPS,
    ModuleInfo,
    SourceInfo,
    Evidence,
)


class TrafficEdgeRuntime:

    """
    Edge-AI runtime coordinator for Module 2 (Traffic Monitoring).

    Coordinates:

    1. Video Processing & Traffic Event Generation
    2. Persistent Offline-First SQLite Event Queue
    3. Background Alert Synchronization to Central Backend
    """

    def __init__(
        self,
        video_source: Optional[VideoSource] = None,
        backend_url: Optional[str] = None,
        sync_interval: Optional[int] = None,
        sync_batch_size: Optional[int] = None,
    ):

        config = Config()

        self.config = config

        # ==================================================
        # VIDEO SOURCE
        # ==================================================

        if video_source is None:

            video_path = config.resolve_path(
                config.traffic_input_video
            )

            video_source = FileVideoSource(
                video_path
            )

        self.video_source = video_source

        # ==================================================
        # BACKEND
        # ==================================================

        self.backend_url = (
            backend_url
            if backend_url is not None
            else config.backend_url
        ).rstrip("/")

        # ==================================================
        # LOCAL QUEUE
        # ==================================================

        queue_db = config.resolve_path(
            config.traffic_queue_database
        )

        self.queue = AlertQueue(
            database_path=queue_db
        )

        # ==================================================
        # ALERT SYNCHRONIZATION
        # ==================================================

        self.sync = AlertSync(
            backend_url=self.backend_url,
            queue=self.queue,
        )

        # ==================================================
        # BACKGROUND WORKER
        # ==================================================

        self.sync_worker = AlertSyncWorker(

            backend_url=self.backend_url,

            interval_seconds=(
                sync_interval
                if sync_interval is not None
                else config.sync_interval
            ),

            batch_size=(
                sync_batch_size
                if sync_batch_size is not None
                else config.sync_batch_size
            ),
        )

        # ==================================================
        # TRAFFIC PROCESSOR
        # ==================================================

        self.processor = TrafficVideoProcessor(
            video_source=self.video_source
        )

    # ======================================================
    # SYNCHRONIZATION
    # ======================================================

    def sync_density_samples(self, density_samples: List[Any]):
        """
        Send aggregated structured JSON traffic density records directly to the backend.
        No images or binary media are transmitted.
        """
        if not density_samples:
            return

        print("\n" + "=" * 60)
        print("MODULE 2 — SYNCHRONIZING TRAFFIC DENSITY JSON STREAM")
        print("=" * 60)
        print(f"Total density samples to synchronize: {len(density_samples)}")

        import json
        import urllib.request

        url = f"{self.backend_url}/traffic/density"
        payload_bytes = json.dumps({"samples": density_samples}).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    print(f"Backend accepted {resp_data.get('saved_samples', len(density_samples))} traffic density samples.")
                else:
                    print(f"Backend returned status {resp.status} for traffic density sync.")
        except Exception as exc:
            print(f"Warning: Could not sync traffic density samples to backend ({exc}). Saved locally.")

    def synchronize(self):

        print("\n" + "=" * 60)


        print(
            "MODULE 2 — EDGE QUEUE SYNCHRONIZATION"
        )

        print("=" * 60)

        print(
            f"Backend: {self.backend_url}"
        )

        print(
            f"Queue before: {self.queue.summary()}"
        )

        # --------------------------------------------------

        if not self.sync.backend_available():

            print(
                "\nBackend unavailable. "
                "Traffic events remain safely in local offline queue."
            )

            return {

                "attempted": 0,

                "sent": 0,

                "failed": 0,

                "backend_available": False,
            }

        # --------------------------------------------------

        result = self.sync.sync(
            limit=20
        )

        result[
            "backend_available"
        ] = True

        print(
            f"Sync result : {result}"
        )

        print(
            f"Queue after : {self.queue.summary()}"
        )

        return result

    # ======================================================
    # BACKGROUND SYNC WORKER
    # ======================================================

    def start_sync_worker(self):

        print(
            "\nStarting background traffic event synchronization..."
        )

        self.sync_worker.start()

    # ------------------------------------------------------

    def stop_sync_worker(self):

        print(
            "\nStopping background synchronization worker..."
        )

        self.sync_worker.stop()

    # ======================================================
    # EVENT -> ALERT CONVERSION
    # ======================================================

    def _convert_to_alert(
        self,
        event: Any,
    ) -> Alert:

        """
        Convert a traffic processor event dictionary into
        the shared Alert schema.
        """

        # --------------------------------------------------
        # ALREADY AN ALERT
        # --------------------------------------------------

        if isinstance(
            event,
            Alert,
        ):

            return event

        # --------------------------------------------------
        # VALIDATE EVENT TYPE
        # --------------------------------------------------

        if not isinstance(
            event,
            dict,
        ):

            raise TypeError(

                "Traffic event must be either an Alert "
                "object or dictionary. "

                f"Received: {type(event)}"
            )

        # --------------------------------------------------
        # DEBUG
        # --------------------------------------------------

        print(
            "\nConverting traffic event to Alert..."
        )

        print(
            f"Event keys: {list(event.keys())}"
        )

        # --------------------------------------------------
        # EXTRACT EVENT DATA
        # --------------------------------------------------

        frame_number = event.get(
            "frame_number",
            0,
        )

        vehicle = event.get(
            "vehicle",
            {},
        )

        analysis = event.get(
            "analysis",
            {},
        )

        counting_summary = event.get(
            "counting_summary",
            {},
        )

        # --------------------------------------------------
        # SEVERITY
        # --------------------------------------------------

        severity = str(
            analysis.get(
                "severity",
                "low",
            )
        ).lower()

        allowed_severities = {

            "low",

            "medium",

            "high",

            "critical",
        }

        if severity not in allowed_severities:

            severity = "low"

        # --------------------------------------------------
        # CREATE ALERT
        # --------------------------------------------------

        alert = Alert(

            # Unique alert ID
            alert_id=str(
                uuid4()
            ),

            # --------------------------------------------------
            # BUS / EDGE DEVICE
            #
            # Replace this later with your real bus identifier
            # if your Config class contains one.
            # --------------------------------------------------

            bus_id=getattr(
                self.config,
                "bus_id",
                "TRAFFIC_EDGE_001",
            ),

            # --------------------------------------------------

            timestamp=datetime.now(
                timezone.utc
            ),

            # --------------------------------------------------
            # GPS
            #
            # Replace with real GPS coordinates when hardware
            # GPS integration is added.
            # --------------------------------------------------

            gps=GPS(

                latitude=float(
                    getattr(
                        self.config,
                        "latitude",
                        0.0,
                    )
                ),

                longitude=float(
                    getattr(
                        self.config,
                        "longitude",
                        0.0,
                    )
                ),

                accuracy_m=float(
                    getattr(
                        self.config,
                        "gps_accuracy_m",
                        0.0,
                    )
                ),
            ),

            # --------------------------------------------------
            # MODULE
            # --------------------------------------------------

            module=ModuleInfo(

                type="traffic",

                version="1.0",
            ),

            # --------------------------------------------------
            # SEVERITY
            # --------------------------------------------------

            severity=severity,

            # --------------------------------------------------
            # PAYLOAD
            #
            # Original traffic event data goes here.
            # --------------------------------------------------

            payload={

                "frame_number":
                    frame_number,

                "vehicle":
                    vehicle,

                "analysis":
                    analysis,

                "counting_summary":
                    counting_summary,
            },

            # --------------------------------------------------
            # SOURCE
            # --------------------------------------------------

            source=SourceInfo(

                device_id=str(
                    getattr(
                        self.config,
                        "device_id",
                        "TRAFFIC_EDGE_DEVICE_001",
                    )
                ),

                camera_id=str(
                    getattr(
                        self.config,
                        "camera_id",
                        "TRAFFIC_CAMERA_001",
                    )
                ),
            ),

            # --------------------------------------------------
            # EVIDENCE
            #
            # Currently None because the event dictionary shown
            # does not include an evidence path.
            # --------------------------------------------------

            evidence=None,
        )

        return alert

    # ======================================================
    # MAIN EDGE RUNTIME
    # ======================================================

    def run(self) -> List[Any]:

        print(
            "\n" + "=" * 60
        )

        print(
            "SMART TRANSPORT EDGE RUNTIME — MODULE 2 (TRAFFIC)"
        )

        print(
            "=" * 60
        )

        # ==================================================
        # STAGE 1
        # ==================================================

        print(
            "\nStage 1: Synchronize existing queued traffic events"
        )

        self.synchronize()

        # ==================================================
        # STAGE 2
        # ==================================================

        print(
            "\nStage 2: Start background sync worker"
        )

        self.start_sync_worker()

        events = []

        try:

            # ==============================================
            # STAGE 3
            # ==============================================

            print(
                "\nStage 3: Run edge traffic vision pipeline"
            )

            events = self.processor.process()

            print(
                f"\nAdding {len(events)} generated "
                "traffic events to edge queue..."
            )

            # ==============================================
            # ENQUEUE 10-SECOND TRAFFIC OBSERVATION ALERTS
            # ==============================================

            queued = 0
            obs_alerts = getattr(self.processor, "observation_alerts", [])
            print(
                f"\nEnqueuing {len(obs_alerts)} 10-second traffic observation alerts..."
            )


            for index, alert in enumerate(
                obs_alerts,
                start=1,
            ):
                print(
                    f"Enqueuing traffic observation {index}/{len(obs_alerts)} (time={alert.payload.get('video_time_seconds')}s, congestion={alert.payload.get('congestion_level')})"
                )
                if self.queue.enqueue(alert):
                    queued += 1

            print(
                f"\nTotal Enqueued: {queued} traffic alerts."
            )

            print(
                f"Queue summary: "
                f"{self.queue.summary()}"
            )


        finally:

            # ==============================================
            # STAGE 4
            # ==============================================

            print(
                "\nStage 4: Final queue synchronization & Traffic Density JSON Stream"
            )

            # Sync structured JSON traffic density records (no images)
            if hasattr(self.processor, "density_samples"):
                self.sync_density_samples(self.processor.density_samples)

            self.synchronize()

            self.stop_sync_worker()


        # ==================================================
        # COMPLETE
        # ==================================================

        print(
            "\n" + "=" * 60
        )

        print(
            "MODULE 2 — EDGE RUNTIME COMPLETE"
        )

        print(
            "=" * 60
        )

        print(
            f"Events generated : "
            f"{len(events)}"
        )

        print(
            f"Queue status     : "
            f"{self.queue.summary()}"
        )

        return events


# ==========================================================
# ENTRY POINT
# ==========================================================

def main():

    runtime = TrafficEdgeRuntime()

    runtime.run()


if __name__ == "__main__":

    main()