from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np


from module2_traffic.camera.source import VideoSource
from module2_traffic.inference.detector import VehicleDetector
from module2_traffic.inference.tracker import VehicleTracker
from module2_traffic.inference.counter import VehicleCounter
from module2_traffic.inference.traffic_analyzer import TrafficAnalyzer
from module2_traffic.inference.heatmap import TrafficHeatmap
from module2_traffic.inference.density_aggregator import TrafficDensityAggregator
from module2_traffic.inference.traffic_observation import TrafficObservationCollector

from shared.config import Config




class TrafficVideoProcessor:
    """
    Complete traffic video processing pipeline.

    Pipeline:

        VideoSource
            ->
        VehicleDetector
            ->
        VehicleTracker
            ->
        VehicleCounter
            ->
        TrafficAnalyzer
            ->
        TrafficHeatmap
            ->
        Annotated output video & Heatmap video
    """

    def __init__(
        self,
        video_source: VideoSource,
        detector: Optional[VehicleDetector] = None,
        tracker: Optional[VehicleTracker] = None,
        counter: Optional[VehicleCounter] = None,
        analyzer: Optional[TrafficAnalyzer] = None,
        heatmap: Optional[TrafficHeatmap] = None,
    ):

        self.config = Config()

        self.video_source = video_source

        self.detector = (
            detector
            if detector is not None
            else VehicleDetector()
        )

        self.tracker = (
            tracker
            if tracker is not None
            else VehicleTracker()
        )

        self.counter = (
            counter
            if counter is not None
            else VehicleCounter()
        )

        self.analyzer = (
            analyzer
            if analyzer is not None
            else TrafficAnalyzer()
        )

        self.heatmap = heatmap

        # Output video paths
        self.output_path = self.config.resolve_path(
            self.config.traffic_output_video
        )

        self.heatmap_output_path = self.config.resolve_path(
            self.config.traffic_heatmap_video
        )

        self.heatmap_image_path = self.config.resolve_path(
            self.config.traffic_heatmap_final_image
        )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.heatmap_output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.events: List[Dict[str, Any]] = []
        self.density_samples: List[Dict[str, Any]] = []
        self.observation_alerts: List[Any] = []



    # ============================================================
    # AUTO COUNT
    # ============================================================

    @staticmethod
    def get_auto_count(
        class_counts: Dict[str, int],
    ) -> int:
        """
        Return the combined auto-rickshaw count.

        Detector normalization should already convert most aliases
        into 'auto rickshaw', but this keeps the HUD robust.
        """

        return (
            class_counts.get("auto rickshaw", 0)
            + class_counts.get("rickshaw", 0)
            + class_counts.get("three wheelers -cng-", 0)
        )

    # ============================================================
    # DRAW DETECTIONS
    # ============================================================

    def draw_detections(
        self,
        frame,
        tracked_detections: List[Dict[str, Any]],
    ):

        annotated = frame

        for det in tracked_detections:

            bbox = det.get("bbox", {})

            xmin = int(bbox.get("xmin", 0))
            ymin = int(bbox.get("ymin", 0))
            xmax = int(bbox.get("xmax", 0))
            ymax = int(bbox.get("ymax", 0))

            class_name = str(
                det.get("class_name", "vehicle")
            )

            confidence = float(
                det.get("confidence", 0.0)
            )

            track_id = det.get("track_id")

            confirmed = bool(
                det.get("confirmed", False)
            )

            if confirmed:
                color = (0, 255, 0)
            else:
                color = (0, 165, 255)

            cv2.rectangle(
                annotated,
                (xmin, ymin),
                (xmax, ymax),
                color,
                2,
            )

            label = (
                f"{class_name} "
                f"ID:{track_id} "
                f"{confidence:.2f}"
            )

            label_y = max(
                20,
                ymin - 8,
            )

            cv2.putText(
                annotated,
                label,
                (xmin, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

            centroid = det.get("centroid")

            if centroid is not None:

                cx = int(centroid[0])
                cy = int(centroid[1])

                cv2.circle(
                    annotated,
                    (cx, cy),
                    4,
                    color,
                    -1,
                )

        return annotated

    # ============================================================
    # DRAW COUNTING LINE
    # ============================================================

    def draw_counting_line(
        self,
        frame,
    ):

        height, width = frame.shape[:2]

        line_y = int(
            height * self.counter.line_ratio
        )

        cv2.line(
            frame,
            (0, line_y),
            (width, line_y),
            (255, 0, 255),
            3,
        )

        cv2.putText(
            frame,
            "COUNTING LINE",
            (20, max(30, line_y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 0, 255),
            2,
        )

        return frame

    # ============================================================
    # DRAW HUD
    # ============================================================

    def draw_hud(
        self,
        frame,
        frame_number,
        total_frames,
        counting_summary,
        analysis,
        active_count,
        heatmap: Optional[TrafficHeatmap] = None,
    ):
        """
        Draw traffic monitoring dashboard with embedded live density heatmap.
        """

        annotated = frame

        height, width = annotated.shape[:2]

        class_counts = counting_summary.get(
            "class_counts",
            {},
        )

        auto_count = self.get_auto_count(
            class_counts
        )

        # Ensure panel fits comfortably inside the video bounds
        panel_width = min(
            450,
            width - 20,
        )

        panel_height = 245

        panel_x1 = width - panel_width - 15
        panel_y1 = 15

        panel_x2 = width - 15
        panel_y2 = panel_y1 + panel_height

        # Semi-transparent solid background
        overlay = annotated.copy()

        cv2.rectangle(
            overlay,
            (panel_x1, panel_y1),
            (panel_x2, panel_y2),
            (18, 18, 18),
            -1,
        )

        annotated = cv2.addWeighted(
            overlay,
            0.85,
            annotated,
            0.15,
            0,
        )

        cv2.rectangle(
            annotated,
            (panel_x1, panel_y1),
            (panel_x2, panel_y2),
            (200, 200, 200),
            1,
        )

        congestion_level = str(
            analysis.get(
                "congestion_level",
                "unknown",
            )
        ).lower()

        congestion_color = (
            0,
            255,
            0,
        )

        if congestion_level == "medium":

            congestion_color = (
                0,
                200,
                255,
            )

        elif congestion_level in (
            "high",
            "critical",
        ):

            congestion_color = (
                0,
                0,
                255,
            )

        # Title
        cv2.putText(
            annotated,
            "TRAFFIC MONITOR",
            (panel_x1 + 15, panel_y1 + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        cv2.line(
            annotated,
            (panel_x1 + 10, panel_y1 + 35),
            (panel_x2 - 10, panel_y1 + 35),
            (100, 100, 100),
            1,
        )

        # Overview
        total_count = counting_summary.get(
            "total_count",
            0,
        )

        cv2.putText(
            annotated,
            f"TOTAL: {total_count}",
            (panel_x1 + 15, panel_y1 + 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
        )

        cv2.putText(
            annotated,
            f"ACTIVE: {active_count}",
            (panel_x1 + 230, panel_y1 + 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
        )

        # Congestion & Occupancy
        occupancy = analysis.get(
            "occupancy_pct",
            0,
        )

        cv2.putText(
            annotated,
            f"CONGESTION: {congestion_level.upper()}",
            (panel_x1 + 15, panel_y1 + 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            congestion_color,
            2,
        )

        cv2.putText(
            annotated,
            f"OCC: {occupancy}%",
            (panel_x1 + 245, panel_y1 + 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            congestion_color,
            2,
        )

        # Section Dividers & Headers
        cv2.line(
            annotated,
            (panel_x1 + 10, panel_y1 + 97),
            (panel_x2 - 10, panel_y1 + 97),
            (70, 70, 70),
            1,
        )

        cv2.putText(
            annotated,
            "VEHICLE COUNTS",
            (panel_x1 + 15, panel_y1 + 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
        )

        cv2.putText(
            annotated,
            "LIVE DENSITY MAP",
            (panel_x1 + 230, panel_y1 + 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
        )

        # Vehicle counts (Left columns)
        left_col_x = panel_x1 + 15
        text_color = (255, 255, 255)

        row_y0 = panel_y1 + 138
        row_step = 22

        cv2.putText(
            annotated,
            f"CAR: {class_counts.get('car', 0)}",
            (left_col_x, row_y0),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            text_color,
            1,
        )

        bike_count = (
            class_counts.get("motorbike", 0)
            + class_counts.get("scooter", 0)
        )
        cv2.putText(
            annotated,
            f"BIKE: {bike_count}",
            (left_col_x + 100, row_y0),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            text_color,
            1,
        )

        cv2.putText(
            annotated,
            f"AUTO: {auto_count}",
            (left_col_x, row_y0 + row_step),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            text_color,
            1,
        )

        cv2.putText(
            annotated,
            f"BUS: {class_counts.get('bus', 0)}",
            (left_col_x + 100, row_y0 + row_step),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            text_color,
            1,
        )

        cv2.putText(
            annotated,
            f"TRUCK: {class_counts.get('truck', 0)}",
            (left_col_x, row_y0 + row_step * 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            text_color,
            1,
        )

        van_count = (
            class_counts.get("van", 0)
            + class_counts.get("minivan", 0)
        )
        cv2.putText(
            annotated,
            f"VAN: {van_count}",
            (left_col_x + 100, row_y0 + row_step * 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            text_color,
            1,
        )

        ambulance_count = class_counts.get("ambulance", 0)
        police_count = class_counts.get("policecar", 0)

        cv2.putText(
            annotated,
            f"AMB: {ambulance_count}",
            (left_col_x, row_y0 + row_step * 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (0, 165, 255),
            1,
        )

        cv2.putText(
            annotated,
            f"POLICE: {police_count}",
            (left_col_x + 100, row_y0 + row_step * 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (0, 165, 255),
            1,
        )

        # ----------------------------------------------------
        # Embedded Live Mini Heatmap (Right section)
        # ----------------------------------------------------
        mini_w = 200
        mini_h = 110
        mini_x = panel_x1 + 230
        mini_y = panel_y1 + 124

        if mini_x + mini_w <= panel_x2 and mini_y + mini_h <= panel_y2:
            if heatmap is not None:
                mini_map = heatmap.get_heatmap_colored()
                mini_map_resized = cv2.resize(
                    mini_map,
                    (mini_w, mini_h),
                    interpolation=cv2.INTER_LINEAR,
                )
            else:
                mini_map_resized = np.zeros(
                    (mini_h, mini_w, 3),
                    dtype=np.uint8,
                )

            # Draw border and insert heatmap thumbnail
            annotated[
                mini_y : mini_y + mini_h,
                mini_x : mini_x + mini_w,
            ] = mini_map_resized

            cv2.rectangle(
                annotated,
                (mini_x, mini_y),
                (mini_x + mini_w, mini_y + mini_h),
                (160, 160, 160),
                1,
            )


        # Frame progress
        if total_frames > 0:

            progress_text = (
                f"FRAME: {frame_number}/{total_frames}"
            )

            cv2.putText(
                annotated,
                progress_text,
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

        return annotated


    # ============================================================
    # PROCESS VIDEO
    # ============================================================

    def process(self) -> List[Dict[str, Any]]:

        print("\n" + "=" * 60)
        print("TRAFFIC VIDEO PROCESSING STARTED")
        print("=" * 60)

        if not self.video_source.open():

            raise RuntimeError(
                "Unable to open video source."
            )

        fps = self.video_source.get_fps()

        frame_width, frame_height = (
            self.video_source.get_resolution()
        )

        total_frames = (
            self.video_source.get_total_frames()
        )

        print(
            f"Resolution : "
            f"{frame_width}x{frame_height}"
        )

        print(
            f"FPS        : {fps}"
        )

        print(
            f"Frames     : {total_frames}"
        )

        # Video writers
        fourcc = cv2.VideoWriter_fourcc(
            *"mp4v"
        )

        writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            fps,
            (
                frame_width,
                frame_height,
            ),
        )

        heatmap_writer = cv2.VideoWriter(
            str(self.heatmap_output_path),
            fourcc,
            fps,
            (
                frame_width,
                frame_height,
            ),
        )

        if not writer.isOpened():

            self.video_source.release()

            raise RuntimeError(
                f"Unable to create output video: "
                f"{self.output_path}"
            )

        if not heatmap_writer.isOpened():

            writer.release()
            self.video_source.release()

            raise RuntimeError(
                f"Unable to create heatmap video: "
                f"{self.heatmap_output_path}"
            )

        # Initialize heatmap accumulator if not provided
        heatmap_component = (
            self.heatmap
            if self.heatmap is not None
            else TrafficHeatmap(
                width=frame_width,
                height=frame_height,
            )
        )

        # Initialize density aggregator for structured traffic density JSON stream
        density_aggregator = TrafficDensityAggregator(
            fps=fps,
            interval_seconds=float(self.config.traffic_observation_interval),
        )

        # Initialize 10-second traffic observation collector
        observation_collector = TrafficObservationCollector(
            fps=fps,
            interval_seconds=10.0,
            config=self.config,
        )

        frame_number = 0
        last_frame = None
        last_analysis = None
        last_counting_summary = None



        try:

            while True:

                success, frame = (
                    self.video_source.read()
                )

                if not success or frame is None:
                    break

                last_frame = frame.copy()
                frame_number += 1


                # ------------------------------------------------
                # 1. DETECT VEHICLES
                # ------------------------------------------------

                detections = self.detector.detect(
                    frame
                )

                # ------------------------------------------------
                # 2. TRACK VEHICLES
                # ------------------------------------------------

                tracked_detections = (
                    self.tracker.update(
                        detections,
                        frame_number,
                    )
                )

                # ------------------------------------------------
                # 3. COUNT LINE CROSSINGS
                # ------------------------------------------------

                counting_summary = (
                    self.counter.update(
                        tracked_detections,
                        frame.shape[0],
                    )
                )

                # ------------------------------------------------
                # 4. ACTIVE VEHICLES
                #
                # Only confirmed tracks are treated as active.
                # ------------------------------------------------

                active_count = sum(
                    1
                    for det in tracked_detections
                    if det.get(
                        "confirmed",
                        False,
                    )
                )

                # ------------------------------------------------
                # 5. TRAFFIC ANALYSIS
                # ------------------------------------------------

                analysis = self.analyzer.analyze(
                    active_vehicle_count=active_count,
                    total_counted=counting_summary[
                        "total_count"
                    ],
                    class_counts=counting_summary[
                        "class_counts"
                    ],
                    directional_counts=counting_summary[
                        "directional_counts"
                    ],
                    frame_width=frame.shape[1],
                    frame_height=frame.shape[0],
                    detections=tracked_detections,
                )

                # ------------------------------------------------
                # 6. SAVE NEW COUNT EVENTS & AGGREGATE TRAFFIC DENSITY
                # ------------------------------------------------

                last_analysis = analysis
                last_counting_summary = counting_summary

                # Collect structured traffic density aggregated samples
                density_sample = density_aggregator.add_frame(
                    frame_number=frame_number,
                    active_vehicle_count=active_count,
                )
                if density_sample is not None:
                    self.density_samples.append(density_sample)

                # Check and generate 10-second traffic observation alert
                obs_alert = observation_collector.check_and_generate(
                    frame_number=frame_number,
                    analysis=analysis,
                    counting_summary=counting_summary,
                    is_final=False,
                )
                if obs_alert is not None:
                    self.observation_alerts.append(obs_alert)


                for counted in counting_summary.get(
                    "newly_counted",
                    [],
                ):

                    event = {
                        "frame_number": frame_number,
                        "vehicle": counted,
                        "analysis": analysis,
                        "counting_summary": {
                            "total_count": (
                                counting_summary[
                                    "total_count"
                                ]
                            ),
                            "class_counts": dict(
                                counting_summary[
                                    "class_counts"
                                ]
                            ),
                            "directional_counts": dict(
                                counting_summary[
                                    "directional_counts"
                                ]
                            ),
                        },
                    }

                    self.events.append(
                        event
                    )


                # ------------------------------------------------
                # 7. TRAFFIC HEATMAP
                # ------------------------------------------------

                centroids = [
                    det["centroid"]
                    for det in tracked_detections
                    if det.get("centroid") is not None
                ]

                heatmap_component.update(centroids)

                heatmap_frame = heatmap_component.render(frame)

                heatmap_writer.write(heatmap_frame)

                # ------------------------------------------------
                # 8. DRAW OUTPUT & HUD WITH EMBEDDED MINI HEATMAP
                # ------------------------------------------------

                annotated = frame.copy()

                annotated = (
                    self.draw_detections(
                        annotated,
                        tracked_detections,
                    )
                )

                annotated = (
                    self.draw_counting_line(
                        annotated
                    )
                )

                annotated = self.draw_hud(
                    annotated,
                    frame_number,
                    total_frames,
                    counting_summary,
                    analysis,
                    active_count,
                    heatmap=heatmap_component,
                )

                writer.write(
                    annotated
                )


                # ------------------------------------------------
                # PROGRESS
                # ------------------------------------------------

                if (
                    frame_number % 30 == 0
                    or frame_number == total_frames
                ):

                    print(
                        f"Processed frame "
                        f"{frame_number}"
                        f"/{total_frames} | "
                        f"Active={active_count} | "
                        f"Total={counting_summary['total_count']} | "
                        f"Congestion="
                        f"{analysis['congestion_level']}"
                    )

        finally:

            writer.release()
            heatmap_writer.release()

            self.video_source.release()

        # Flush any remaining aggregated density sample
        final_sample = density_aggregator.flush()
        if final_sample is not None:
            self.density_samples.append(final_sample)

        # Flush final observation alert if remaining
        if last_analysis and last_counting_summary:
            final_obs = observation_collector.check_and_generate(
                frame_number=frame_number,
                analysis=last_analysis,
                counting_summary=last_counting_summary,
                is_final=True,
            )
            if final_obs is not None:
                self.observation_alerts.append(final_obs)

        # Save final snapshot image
        background_frame = (
            last_frame
            if last_frame is not None
            else np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        )
        final_heatmap_image = heatmap_component.render(background_frame, alpha=0.55)
        cv2.imwrite(str(self.heatmap_image_path), final_heatmap_image)




        print("\n" + "=" * 60)
        print("TRAFFIC VIDEO PROCESSING COMPLETE")
        print("=" * 60)

        print(
            f"Total frames processed: "
            f"{frame_number}"
        )

        print(
            f"Total vehicles counted: "
            f"{self.counter.total_count}"
        )

        print(
            f"Events generated: "
            f"{len(self.events)}"
        )

        print(
            f"Annotated video: "
            f"{self.output_path}"
        )

        print(
            f"Heatmap video: "
            f"{self.heatmap_output_path}"
        )

        print(
            f"Final heatmap image: "
            f"{self.heatmap_image_path}"
        )

        return self.events



def main():

    from module2_traffic.camera.source import (
        FileVideoSource,
    )

    config = Config()

    video_path = config.resolve_path(
        config.traffic_input_video
    )

    source = FileVideoSource(
        video_path
    )

    processor = TrafficVideoProcessor(
        video_source=source
    )

    processor.process()


if __name__ == "__main__":
    main()