from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np

from shared.camera.frame_packet import FramePacket
from shared.schemas.alert_schema import Alert
from shared.config import Config

from module2_traffic.inference.detector import VehicleDetector
from module2_traffic.inference.tracker import VehicleTracker
from module2_traffic.inference.counter import VehicleCounter
from module2_traffic.inference.traffic_analyzer import TrafficAnalyzer
from module2_traffic.inference.density_aggregator import TrafficDensityAggregator
from module2_traffic.inference.traffic_observation import TrafficObservationCollector


class Module2TrafficAdapter:
    """
    Adapter enabling Module 2 Traffic Monitoring to process individual frames
    from the SharedVideoSource FramePacket stream without opening a separate capture.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        fps: float = 25.0,
        gps_service: Optional[Any] = None,
    ):
        self.config = config or Config()
        self.fps = fps if fps > 0 else 25.0
        self.gps_service = gps_service

        self.detector = VehicleDetector(
            confidence=float(self.config.traffic_confidence)
        )
        self.tracker = VehicleTracker(
            iou_threshold=float(self.config.traffic_tracker_iou),
            max_missing_frames=int(self.config.traffic_tracker_max_missing),
            confirmation_hits=int(self.config.traffic_tracker_confirmation_hits),
        )
        self.counter = VehicleCounter(
            line_ratio=float(self.config.traffic_counting_line_position),
            direction_enabled=bool(self.config.traffic_counting_direction_enabled),
        )
        self.analyzer = TrafficAnalyzer(
            low_threshold=int(self.config.traffic_low_threshold),
            medium_threshold=int(self.config.traffic_medium_threshold),
            high_threshold=int(self.config.traffic_high_threshold),
            observation_interval=int(self.config.traffic_observation_interval),
        )

        # Aggregators with explicit shared GPS service
        self.density_aggregator = TrafficDensityAggregator(
            fps=self.fps,
            interval_seconds=float(self.config.traffic_observation_interval),
            gps_service=self.gps_service,
        )
        self.observation_collector = TrafficObservationCollector(
            fps=self.fps,
            interval_seconds=float(self.config.traffic_observation_interval),
            gps_service=self.gps_service,
            config=self.config,
        )

        self.density_samples: List[Dict[str, Any]] = []
        self.observation_alerts: List[Alert] = []
        self.events: List[Dict[str, Any]] = []

        self.last_analysis: Optional[Dict[str, Any]] = None
        self.last_counting_summary: Optional[Dict[str, Any]] = None
        self.processed_frames = 0

    def process_frame(self, packet: FramePacket) -> List[Alert]:
        """
        Process a single FramePacket from the shared camera pipeline.
        Runs vehicle detection, tracking, counting, and 10s observation telemetry.
        Returns newly generated observation alerts if an observation interval triggers.
        """
        frame_number = packet.frame_number
        frame = packet.frame
        height, width = frame.shape[:2]

        self.processed_frames += 1

        # 1. Vehicle detection (YOLO)
        detections = self.detector.detect(frame)

        # 2. Vehicle multi-object tracking
        tracked_detections = self.tracker.update(detections, frame_number)

        # 3. Virtual line crossing counter
        counting_summary = self.counter.update(tracked_detections, height)

        # 4. Active vehicle counting (confirmed tracks only)
        active_count = sum(1 for det in tracked_detections if det.get("confirmed", False))

        # 5. Traffic congestion analysis
        analysis = self.analyzer.analyze(
            active_vehicle_count=active_count,
            total_counted=counting_summary["total_count"],
            class_counts=counting_summary["class_counts"],
            directional_counts=counting_summary["directional_counts"],
            frame_width=width,
            frame_height=height,
            detections=tracked_detections,
        )

        self.last_analysis = analysis
        self.last_counting_summary = counting_summary

        # 6. Aggregate density samples
        density_sample = self.density_aggregator.add_frame(
            frame_number=frame_number,
            active_vehicle_count=active_count,
        )
        if density_sample is not None:
            self.density_samples.append(density_sample)

        # 7. Check and generate 10-second traffic observation alert
        new_alerts: List[Alert] = []
        obs_alert = self.observation_collector.check_and_generate(
            frame_number=frame_number,
            analysis=analysis,
            counting_summary=counting_summary,
            is_final=False,
        )
        if obs_alert is not None:
            self.observation_alerts.append(obs_alert)
            new_alerts.append(obs_alert)

        # Save line-crossing event records internally
        for counted in counting_summary.get("newly_counted", []):
            event = {
                "frame_number": frame_number,
                "vehicle": counted,
                "analysis": analysis,
                "counting_summary": dict(counting_summary),
            }
            self.events.append(event)

        return new_alerts

    def finalize(self, total_frames: int) -> List[Alert]:
        """
        Flush remaining buffered density samples and final observation alert on stream end.
        """
        final_sample = self.density_aggregator.flush()
        if final_sample is not None:
            self.density_samples.append(final_sample)

        new_alerts = []
        if self.last_analysis and self.last_counting_summary:
            final_obs = self.observation_collector.check_and_generate(
                frame_number=total_frames,
                analysis=self.last_analysis,
                counting_summary=self.last_counting_summary,
                is_final=True,
            )
            if final_obs is not None:
                self.observation_alerts.append(final_obs)
                new_alerts.append(final_obs)

        return new_alerts

    def get_summary(self) -> dict:
        return {
            "processed_frames": self.processed_frames,
            "total_counted": self.counter.total_count,
            "active_vehicles": self.last_analysis.get("active_vehicle_count", 0) if self.last_analysis else 0,
            "congestion_level": self.last_analysis.get("congestion_level", "low") if self.last_analysis else "low",
            "observation_alerts": len(self.observation_alerts),
            "density_samples": len(self.density_samples),
        }
