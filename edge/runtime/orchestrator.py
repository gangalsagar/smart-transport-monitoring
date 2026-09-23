import sys
import argparse
import time
from pathlib import Path
from typing import Optional, List
import urllib.request
import json

from shared.camera.shared_video_source import SharedVideoSource
from shared.camera.frame_packet import FramePacket
from shared.config import Config
from shared.schemas.alert_schema import Alert
from shared.gps.gps_service import SharedGPSService
from shared.gps.gps_fix import GPSFix

from module1_road_defect.adapter import Module1RoadDefectAdapter
from module2_traffic.adapter import Module2TrafficAdapter
from module3_incident_monitoring.adapter import Module3IncidentAdapter
from module4_passenger_demand.adapter import Module4PassengerDemandAdapter

# Global Edge Storage
from edge.storage.alert_queue import AlertQueue
from edge.storage.alert_sync import AlertSync
from edge.storage.sync_worker import AlertSyncWorker


class EdgeOrchestrator:
    """
    Unified Edge Runtime Coordinator.
    
    Implements the target single-camera, single-GPS architecture:
    ONE Shared Video/Camera Source (File Video or Live Connected Mobile Camera)
           |
           +-----------------------+
           |                       |
           v                       v
      FramePacket          SharedGPSService (Windows Laptop Location)
           |                       |
      +----+----+----+        +----+----+----+
      |         |    |        |         |    |
      v         v    v        v         v    v
    Module 1 Module 2 Module 3  Module 1 Module 2 Module 3
    (Defects)(Traffic)(Incident)(GPS Fix)(GPS Fix)(GPS Fix)
      |         |    |
      +----+----+----+
           |
           v
     Alert Queue & Backend Sync
    """

    def __init__(
        self,
        video_source_path_or_index: Optional[str | int | Path] = None,
        source_mode: Optional[str] = None,
        camera_index: Optional[int] = None,
        backend_url: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        self.config = config or Config()

        # Determine source mode ("file" | "live")
        mode = (source_mode or self.config.shared_camera_source).lower()

        if video_source_path_or_index is not None:
            self.source_path = video_source_path_or_index
        elif mode == "live":
            idx = camera_index if camera_index is not None else self.config.shared_camera_index
            self.source_path = int(idx)
        else:
            combined_path = self.config.combined_input_video
            resolved = self.config.resolve_path(combined_path)
            if not resolved.exists():
                fallback = self.config.resolve_path("module2_traffic/data/videos/test_video.mp4")
                if fallback.exists():
                    self.source_path = fallback
                else:
                    self.source_path = resolved
            else:
                self.source_path = resolved

        self.backend_url = (backend_url or self.config.backend_url).rstrip("/")

        # Initialize single shared camera / video source
        self.shared_source = SharedVideoSource(self.source_path)

        # Initialize centralized SharedGPSService (ONE instance)
        self.gps_service = SharedGPSService.get_instance(
            provider_type=self.config.shared_gps_provider,
            poll_interval_seconds=self.config.shared_gps_poll_interval,
            stale_threshold_seconds=self.config.shared_gps_stale_threshold,
            config=self.config,
        )

        # Module Adapters
        self.module1_adapter: Optional[Module1RoadDefectAdapter] = None
        self.module2_adapter: Optional[Module2TrafficAdapter] = None
        self.module3_adapter: Optional[Module3IncidentAdapter] = None
        self.module4_adapter: Optional[Module4PassengerDemandAdapter] = None

        # Persistent Storage (Check edge data directory first)
        edge_db_path = self.config.resolve_path("edge/data/alerts/alert_queue.db")
        if not edge_db_path.parent.exists():
            edge_db_path = self.config.resolve_path("module1_road_defect/data/alerts/alert_queue.db")

        self.queue = AlertQueue(database_path=edge_db_path)
        self.sync = AlertSync(backend_url=self.backend_url, queue=self.queue)
        self.sync_worker = AlertSyncWorker(
            backend_url=self.backend_url,
            interval_seconds=self.config.sync_interval,
            batch_size=self.config.sync_batch_size,
        )
        self._last_synced_density_idx = 0

    def run(self, max_frames: Optional[int] = None) -> dict:
        """
        Execute the unified edge pipeline across all frames of the shared source.
        In live camera mode, continues indefinitely until Ctrl+C or max_frames is reached.
        """
        print("\n" + "=" * 60)
        print("UNIFIED EDGE RUNTIME STARTED")
        print("=" * 60)
        print(f"Mode         : {'LIVE CAMERA (Connected Mobile Camera)' if self.shared_source.is_live_camera or isinstance(self.source_path, int) else 'FILE VIDEO'}")
        print(f"Video Source : {self.source_path}")
        print(f"Backend URL  : {self.backend_url}")

        # 1. Start Shared GPS Service once
        print("\nStarting Shared GPS Service...")
        self.gps_service.start()
        active_gps = self.gps_service.get_latest_fix()
        print(f"Shared GPS     : ACTIVE (Provider={self.gps_service.active_provider_name}, Source={active_gps.source})")
        if active_gps.valid:
            print(f"Initial Fix    : Lat={active_gps.latitude:.6f}, Lng={active_gps.longitude:.6f} (Acc={active_gps.accuracy_m:.1f}m)")
        else:
            print(f"Initial Fix    : Waiting for location ({active_gps.status})")

        # 2. Open shared capture once
        print("\nOpening single shared camera capture...")
        try:
            self.shared_source.open()
        except Exception as exc:
            print(f"\n[FATAL ERROR] {exc}")
            self.gps_service.stop()
            raise SystemExit(1)

        fps = self.shared_source.fps
        width, height = self.shared_source.resolution
        total_frames = self.shared_source.total_frames
        stream_desc = "LIVE STREAM (Ctrl+C to stop)" if self.shared_source.is_live_camera else f"{total_frames} frames"
        print(f"Shared capture : ACTIVE ({width}x{height} @ {fps:.1f} FPS, total={stream_desc})")

        # 3. Initialize Module Adapters with shared stream and GPS service
        print("\nInitializing Module 1 (Road Defect)...")
        self.module1_adapter = Module1RoadDefectAdapter(
            config=self.config,
            gps_service=self.gps_service,
        )
        print("Module 1 initialized : YES")

        print("\nInitializing Module 2 (Traffic Monitoring)...")
        self.module2_adapter = Module2TrafficAdapter(
            config=self.config,
            fps=fps,
            gps_service=self.gps_service,
        )
        print("Module 2 initialized : YES")

        print("\nInitializing Module 3 (Incident & Rash Driving)...")
        self.module3_adapter = Module3IncidentAdapter(
            config=self.config,
            gps_service=self.gps_service,
        )
        print("Module 3 initialized : YES")

        if self.config.module4_enabled:
            print("\nInitializing Module 4 (Passenger Demand Intelligence)...")
            self.module4_adapter = Module4PassengerDemandAdapter(
                config=self.config,
                gps_service=self.gps_service,
            )
            print("Module 4 initialized : YES (Data-Driven, Event-Based)")

        # 4. Start background alert sync worker
        print("\nStarting background synchronization worker...")
        self.sync_worker.start()

        processed_frame_count = 0
        total_m1_alerts = 0
        total_m2_alerts = 0
        total_m3_alerts = 0

        start_time = time.time()

        try:
            while True:
                # Read single FramePacket
                packet: Optional[FramePacket] = self.shared_source.read_packet()
                if packet is None:
                    if self.shared_source.is_live_camera:
                        print("\n[WARNING] Live camera frame read returned empty. Retrying...")
                        time.sleep(0.05)
                        continue
                    else:
                        break

                processed_frame_count += 1
                frame_no = packet.frame_number

                # 5. Distribute EXACT SAME FramePacket to Module 1
                m1_alerts = self.module1_adapter.process_frame(packet)
                for alert in m1_alerts:
                    self.queue.enqueue(alert)
                    total_m1_alerts += 1

                # 6. Distribute EXACT SAME FramePacket to Module 2
                m2_alerts = self.module2_adapter.process_frame(packet)
                for alert in m2_alerts:
                    self.queue.enqueue(alert)
                    total_m2_alerts += 1

                # 7. Distribute EXACT SAME FramePacket to Module 3
                if self.module3_adapter:
                    m3_alerts = self.module3_adapter.process_frame(packet)
                    for alert in m3_alerts:
                        row_id = self.queue.enqueue(alert)
                        total_m3_alerts += 1

                        # CRITICAL EMERGENCY PRIORITY: Immediate dispatch attempt
                        if alert.severity == "critical" or alert.payload.get("assigned_team") == "emergency_team":
                            try:
                                sent_ok = self.sync.send_alert(alert)
                                if sent_ok and row_id:
                                    self.queue.mark_sent(row_id)
                                    print(f"  [PRIORITY DISPATCH] Critical incident {alert.alert_id} immediately sent to backend.")
                            except Exception as sync_err:
                                # Safe queue persistence fallback
                                print(f"  [PRIORITY RETRY QUEUED] Critical incident {alert.alert_id} retained in queue: {sync_err}")

                # Periodic progress logging (every 30 frames)
                if frame_no % 30 == 0 or (total_frames > 0 and frame_no == total_frames):
                    cur_gps = self.gps_service.get_latest_fix()
                    gps_str = f"Lat={cur_gps.latitude:.4f}, Lng={cur_gps.longitude:.4f}" if cur_gps.valid else f"GPS={cur_gps.status}"
                    total_str = f"/{total_frames}" if total_frames > 0 else ""
                    print(
                        f"Frame {frame_no:4d}{total_str} | "
                        f"M1={total_m1_alerts} | "
                        f"M2 Active={self.module2_adapter.last_analysis.get('active_vehicle_count', 0) if self.module2_adapter.last_analysis else 0} | "
                        f"M3 Incidents={total_m3_alerts} | "
                        f"{gps_str}"
                    )

                # Periodic live traffic density sync (every 60 frames)
                if frame_no % 60 == 0:
                    self._sync_traffic_density()

                if max_frames and processed_frame_count >= max_frames:
                    print(f"\nReached configured max_frames ({max_frames}). Stopping gracefully.")
                    break

            # Finalize Module 2 stream (flush remaining density / final observation)
            final_m2_alerts = self.module2_adapter.finalize(processed_frame_count)
            for alert in final_m2_alerts:
                self.queue.enqueue(alert)
                total_m2_alerts += 1

        except KeyboardInterrupt:
            print("\nReceived user interrupt (Ctrl+C). Shutting down unified pipeline...")
        finally:
            # Clean resource release
            self.shared_source.release()
            print("\nShared video capture released.")

            self.gps_service.stop()
            print("Shared GPS service stopped.")

        elapsed = time.time() - start_time
        fps_achieved = processed_frame_count / elapsed if elapsed > 0 else 0.0

        # Post Traffic Density JSON stream to backend
        self._sync_traffic_density()

        # Stop background sync worker and perform final queue flush
        self.sync_worker.stop()
        final_sync = self.sync.sync(limit=100)

        print("\n" + "=" * 60)
        print("UNIFIED EDGE RUNTIME COMPLETE")
        print("=" * 60)
        print(f"Total Frames Processed : {processed_frame_count}")
        print(f"Time Elapsed           : {elapsed:.2f} s ({fps_achieved:.1f} FPS)")
        print(f"Module 1 Alerts        : {total_m1_alerts}")
        print(f"Module 2 Alerts        : {total_m2_alerts}")
        print(f"Module 3 Alerts        : {total_m3_alerts}")
        print(f"Final Sync Result      : {final_sync}")

        return {
            "frames_processed": processed_frame_count,
            "module1_alerts": total_m1_alerts,
            "module2_alerts": total_m2_alerts,
            "module3_alerts": total_m3_alerts,
            "elapsed_seconds": round(elapsed, 2),
            "fps": round(fps_achieved, 1),
            "final_sync": final_sync,
        }

    def _sync_traffic_density(self):
        """Send newly aggregated traffic density samples to backend incrementally."""
        if not self.module2_adapter or not self.module2_adapter.density_samples:
            return

        all_samples = self.module2_adapter.density_samples
        if self._last_synced_density_idx >= len(all_samples):
            return

        new_samples = all_samples[self._last_synced_density_idx:]
        density_url = f"{self.backend_url}/traffic/density"
        try:
            payload = json.dumps({
                "device_id": self.config.device_id,
                "bus_id": self.config.bus_id,
                "samples": new_samples,
            }).encode("utf-8")

            req = urllib.request.Request(
                density_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    self._last_synced_density_idx = len(all_samples)
                    print(f"Synchronized {len(new_samples)} new traffic density samples to backend (total: {len(all_samples)}).")
        except Exception as e:
            print(f"Traffic density sync warning (non-fatal): {e}")


def main():
    parser = argparse.ArgumentParser(description="Unified Edge Orchestrator (Shared Camera + Shared GPS)")
    parser.add_argument("--source", choices=["file", "live"], default=None, help="Camera source mode ('file' or 'live')")
    parser.add_argument("--index", type=int, default=None, help="Live camera device index (default: 1 for connected mobile camera)")
    parser.add_argument("--video", type=str, default=None, help="Path to video file (if source mode is file)")
    parser.add_argument("--frames", type=int, default=None, help="Optional max frames limit (useful for testing)")

    args = parser.parse_args()

    orchestrator = EdgeOrchestrator(
        video_source_path_or_index=args.video,
        source_mode=args.source,
        camera_index=args.index,
    )
    orchestrator.run(max_frames=args.frames)


if __name__ == "__main__":
    main()
