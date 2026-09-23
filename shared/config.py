from pathlib import Path
from typing import Any

import yaml


class Config:
    """
    Central configuration loader.

    Loads config/config.yaml once and provides
    convenient access to nested configuration values.
    """

    def __init__(self, config_path=None):

        project_root = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

        if config_path is None:
            config_path = (
                project_root
                / "config"
                / "config.yaml"
            )

        self.config_path = Path(
            config_path
        )

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found:\n"
                f"{self.config_path}"
            )

        with self.config_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            self.data = yaml.safe_load(file)

        if not isinstance(
            self.data,
            dict
        ):
            raise ValueError(
                "Configuration file must contain "
                "a YAML object."
            )

    # ========================================================
    # GENERIC ACCESS
    # ========================================================

    def get(
        self,
        *keys,
        default=None
    ) -> Any:
        """
        Read a nested configuration value.

        Example:

            config.get(
                "backend",
                "url"
            )
        """

        value = self.data

        for key in keys:

            if not isinstance(
                value,
                dict
            ):

                return default

            if key not in value:

                return default

            value = value[key]

        return value

    # ========================================================
    # SHARED CAMERA & UNIFIED PIPELINE
    # ========================================================

    @property
    def shared_camera_enabled(self):
        return bool(
            self.get(
                "shared_camera",
                "enabled",
                default=True
            )
        )

    @property
    def combined_input_video(self):
        return self.get(
            "shared_camera",
            "combined_input_video",
            default="data/videos/combined_test_video.mp4"
        )

    @property
    def shared_camera_source(self):
        return str(
            self.get(
                "shared_camera",
                "source",
                default="file"
            )
        )

    @property
    def shared_camera_index(self):
        return int(
            self.get(
                "shared_camera",
                "camera_index",
                default=1
            )
        )

    # ========================================================
    # SHARED GPS ARCHITECTURE
    # ========================================================

    @property
    def shared_gps_provider(self):
        return str(
            self.get(
                "gps",
                "provider",
                default="laptop"
            )
        )

    @property
    def shared_gps_poll_interval(self):
        return float(
            self.get(
                "gps",
                "poll_interval_seconds",
                default=1.0
            )
        )

    @property
    def shared_gps_stale_threshold(self):
        return float(
            self.get(
                "gps",
                "stale_threshold_seconds",
                default=15.0
            )
        )

    # ========================================================
    # MODULE 1
    # ========================================================

    @property
    def module1(self):

        return self.data[
            "module1_road_defect"
        ]

    @property
    def model_path(self):

        return self.get(
            "module1_road_defect",
            "model",
            "path"
        )

    @property
    def confidence(self):

        return float(
            self.get(
                "module1_road_defect",
                "model",
                "confidence",
                default=0.28
            )
        )

    @property
    def image_size(self):

        return int(
            self.get(
                "module1_road_defect",
                "model",
                "image_size",
                default=640
            )
        )

    @property
    def inference_device(self):

        return self.get(
            "module1_road_defect",
            "model",
            "device",
            default=0
        )

    @property
    def frame_skip(self):

        return int(
            self.get(
                "module1_road_defect",
                "vision",
                "frame_skip",
                default=5
            )
        )

    @property
    def input_video(self):

        return self.get(
            "module1_road_defect",
            "vision",
            "input_video"
        )

    @property
    def output_video(self):

        return self.get(
            "module1_road_defect",
            "vision",
            "output_video"
        )

    # ========================================================
    # TRACKER
    # ========================================================

    @property
    def tracker_iou_threshold(self):

        return float(
            self.get(
                "module1_road_defect",
                "tracker",
                "iou_threshold",
                default=0.30
            )
        )

    @property
    def tracker_confirmation_hits(self):

        return int(
            self.get(
                "module1_road_defect",
                "tracker",
                "confirmation_hits",
                default=2
            )
        )

    @property
    def tracker_max_missing_frames(self):

        return int(
            self.get(
                "module1_road_defect",
                "tracker",
                "max_missing_frames",
                default=30
            )
        )

    # ========================================================
    # GPS
    # ========================================================

    @property
    def gps_mode(self):

        return self.get(
            "module1_road_defect",
            "gps",
            "mode",
            default="simulated"
        )

    @property
    def phone_gps_endpoint(self):

        return self.get(
            "module1_road_defect",
            "gps",
            "phone",
            "endpoint"
        )

    @property
    def phone_gps_timeout(self):

        return int(
            self.get(
                "module1_road_defect",
                "gps",
                "phone",
                "timeout",
                default=3
            )
        )

    @property
    def phone_gps_max_age(self):

        return int(
            self.get(
                "module1_road_defect",
                "gps",
                "phone",
                "max_age_seconds",
                default=10
            )
        )

    @property
    def gnss_port(self):

        return self.get(
            "module1_road_defect",
            "gps",
            "gnss",
            "port"
        )

    @property
    def gnss_baudrate(self):

        return int(
            self.get(
                "module1_road_defect",
                "gps",
                "gnss",
                "baudrate",
                default=9600
            )
        )

    @property
    def gnss_timeout(self):

        return int(
            self.get(
                "module1_road_defect",
                "gps",
                "gnss",
                "timeout",
                default=2
            )
        )

    # ========================================================
    # DEVICE
    # ========================================================

    @property
    def bus_id(self):

        return self.get(
            "module1_road_defect",
            "device",
            "bus_id",
            default="BUS-TEST"
        )

    @property
    def device_id(self):

        return self.get(
            "module1_road_defect",
            "device",
            "device_id",
            default="EDGE-01"
        )

    @property
    def camera_id(self):

        return self.get(
            "module1_road_defect",
            "device",
            "camera_id",
            default="FRONT_CAM"
        )

    # ========================================================
    # BACKEND
    # ========================================================

    @property
    def backend_enabled(self):

        return bool(
            self.get(
                "backend",
                "enabled",
                default=True
            )
        )

    @property
    def backend_url(self):

        return self.get(
            "backend",
            "url",
            default="http://127.0.0.1:8001"
        )

    @property
    def backend_timeout(self):

        return int(
            self.get(
                "backend",
                "timeout",
                default=5
            )
        )

    # ========================================================
    # SYNC
    # ========================================================

    @property
    def sync_enabled(self):

        return bool(
            self.get(
                "sync",
                "enabled",
                default=True
            )
        )

    @property
    def sync_interval(self):

        return int(
            self.get(
                "sync",
                "interval_seconds",
                default=5
            )
        )

    @property
    def sync_batch_size(self):

        return int(
            self.get(
                "sync",
                "batch_size",
                default=20
            )
        )

    # ========================================================
    # STORAGE
    # ========================================================

    @property
    def alert_file(self):

        return self.get(
            "module1_road_defect",
            "storage",
            "alert_file"
        )

    @property
    def queue_database(self):

        return self.get(
            "module1_road_defect",
            "storage",
            "queue_database"
        )

    @property
    def evidence_directory(self):

        return self.get(
            "module1_road_defect",
            "storage",
            "evidence_directory"
        )

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def resolve_path(self, path_str: str) -> Path:
        if path_str is None:
            return self.project_root
        p = Path(path_str)
        if p.is_absolute():
            return p
        return self.project_root / p

    # ========================================================
    # MODULE 2 — TRAFFIC
    # ========================================================

    @property
    def module2(self):
        return self.data.get("module2_traffic", {})

    @property
    def traffic_model_path(self):
        return self.get(
            "module2_traffic",
            "model",
            "path",
            default="yolov8s.pt"
        )

    @property
    def traffic_confidence(self):
        return float(
            self.get(
                "module2_traffic",
                "model",
                "confidence",
                default=0.35
            )
        )

    @property
    def traffic_image_size(self):
        return int(
            self.get(
                "module2_traffic",
                "model",
                "image_size",
                default=640
            )
        )

    @property
    def traffic_inference_device(self):
        return self.get(
            "module2_traffic",
            "model",
            "device",
            default=0
        )

    @property
    def traffic_classes(self):
        return self.get(
            "module2_traffic",
            "model",
            "classes",
            default=["car", "bus", "truck", "motorcycle"]
        )

    @property
    def traffic_frame_skip(self):
        return int(
            self.get(
                "module2_traffic",
                "vision",
                "frame_skip",
                default=3
            )
        )

    @property
    def traffic_input_video(self):
        return self.get(
            "module2_traffic",
            "vision",
            "input_video",
            default="module2_traffic/data/videos/test_video.mp4"
        )

    @property
    def traffic_output_video(self):
        return self.get(
            "module2_traffic",
            "vision",
            "output_video",
            default="module2_traffic/data/output/traffic_annotated.mp4"
        )

    @property
    def traffic_heatmap_video(self):
        return self.get(
            "module2_traffic",
            "vision",
            "heatmap_video",
            default="module2_traffic/data/output/traffic_heatmap.mp4"
        )

    @property
    def traffic_heatmap_final_image(self):
        return self.get(
            "module2_traffic",
            "vision",
            "heatmap_final_image",
            default="module2_traffic/data/output/traffic_heatmap_final.jpg"
        )

    @property
    def traffic_heatmap_radius(self):
        return int(
            self.get(
                "module2_traffic",
                "heatmap",
                "radius",
                default=30
            )
        )

    @property
    def traffic_heatmap_decay(self):
        return float(
            self.get(
                "module2_traffic",
                "heatmap",
                "decay",
                default=1.0
            )
        )

    @property
    def traffic_heatmap_alpha(self):
        return float(
            self.get(
                "module2_traffic",
                "heatmap",
                "alpha",
                default=0.45
            )
        )


    @property
    def traffic_tracker_iou(self):
        return float(
            self.get(
                "module2_traffic",
                "tracker",
                "iou_threshold",
                default=0.30
            )
        )

    @property
    def traffic_tracker_max_missing(self):
        return int(
            self.get(
                "module2_traffic",
                "tracker",
                "max_missing_frames",
                default=20
            )
        )

    @property
    def traffic_tracker_confirmation_hits(self):
        return int(
            self.get(
                "module2_traffic",
                "tracker",
                "confirmation_hits",
                default=2
            )
        )

    @property
    def traffic_counting_line_position(self):
        return float(
            self.get(
                "module2_traffic",
                "counting",
                "line_position",
                default=0.60
            )
        )

    @property
    def traffic_counting_direction_enabled(self):
        return bool(
            self.get(
                "module2_traffic",
                "counting",
                "direction_enabled",
                default=True
            )
        )

    @property
    def traffic_low_threshold(self):
        return int(
            self.get(
                "module2_traffic",
                "traffic",
                "low_threshold",
                default=5
            )
        )

    @property
    def traffic_medium_threshold(self):
        return int(
            self.get(
                "module2_traffic",
                "traffic",
                "medium_threshold",
                default=12
            )
        )

    @property
    def traffic_high_threshold(self):
        return int(
            self.get(
                "module2_traffic",
                "traffic",
                "high_threshold",
                default=20
            )
        )

    @property
    def traffic_observation_interval(self):
        return int(
            self.get(
                "module2_traffic",
                "traffic",
                "observation_interval_seconds",
                default=5
            )
        )

    @property
    def traffic_bus_id(self):
        return self.get(
            "module2_traffic",
            "device",
            "bus_id",
            default="BUS-TEST"
        )

    @property
    def traffic_device_id(self):
        return self.get(
            "module2_traffic",
            "device",
            "device_id",
            default="EDGE-01"
        )

    @property
    def traffic_camera_id(self):
        return self.get(
            "module2_traffic",
            "device",
            "camera_id",
            default="FRONT_CAM"
        )

    @property
    def traffic_alert_file(self):
        return self.get(
            "module2_traffic",
            "storage",
            "alert_file",
            default="module2_traffic/data/alerts/traffic_events.jsonl"
        )

    @property
    def traffic_queue_database(self):
        return self.get(
            "module2_traffic",
            "storage",
            "queue_database",
            default="module2_traffic/data/alerts/traffic_queue.db"
        )

    @property
    def traffic_evidence_directory(self):
        return self.get(
            "module2_traffic",
            "storage",
            "evidence_directory",
            default="module2_traffic/data/evidence"
        )

    # ========================================================
    # MODULE 4: PASSENGER DEMAND INTELLIGENCE
    # ========================================================

    @property
    def module4_enabled(self):
        return bool(
            self.get(
                "module4_passenger_demand",
                "enabled",
                default=True
            )
        )

    @property
    def passenger_bus_id(self):
        return str(
            self.get(
                "module4_passenger_demand",
                "bus_id",
                default="BUS-102"
            )
        )

    @property
    def passenger_default_route_id(self):
        return str(
            self.get(
                "module4_passenger_demand",
                "default_route_id",
                default="25A"
            )
        )

    @property
    def passenger_bus_capacity(self):
        return int(
            self.get(
                "module4_passenger_demand",
                "bus_capacity",
                default=60
            )
        )

    @property
    def passenger_duplicate_window_seconds(self):
        return float(
            self.get(
                "module4_passenger_demand",
                "duplicate_window_seconds",
                default=15.0
            )
        )

    @property
    def passenger_abnormal_submission_window_seconds(self):
        return float(
            self.get(
                "module4_passenger_demand",
                "abnormal_submission_window_seconds",
                default=20.0
            )
        )

    @property
    def passenger_abnormal_submission_threshold(self):
        return int(
            self.get(
                "module4_passenger_demand",
                "abnormal_submission_threshold",
                default=8
            )
        )

    @property
    def passenger_dataset_path(self):
        return str(
            self.get(
                "module4_passenger_demand",
                "pass_dataset",
                "path",
                default="data/passenger/bus_passes.csv"
            )
        )

    @property
    def passenger_demand_thresholds(self):
        return {
            "low": float(self.get("module4_passenger_demand", "demand_thresholds", "low_load_factor", default=0.50)),
            "normal": float(self.get("module4_passenger_demand", "demand_thresholds", "normal_load_factor", default=0.85)),
            "high": float(self.get("module4_passenger_demand", "demand_thresholds", "high_load_factor", default=1.15)),
            "critical": float(self.get("module4_passenger_demand", "demand_thresholds", "critical_load_factor", default=1.40)),
        }


def main():

    print("=" * 60)
    print("CONFIGURATION TEST")
    print("=" * 60)

    config = Config()

    print(
        f"\nConfig file:"
        f"\n{config.config_path}"
    )

    print(
        "\nModule 1:"
    )

    print(
        f"  Model       : "
        f"{config.model_path}"
    )

    print(
        f"  Confidence  : "
        f"{config.confidence}"
    )

    print(
        f"  Image size  : "
        f"{config.image_size}"
    )

    print(
        f"  Frame skip  : "
        f"{config.frame_skip}"
    )

    print(
        f"  GPS mode    : "
        f"{config.gps_mode}"
    )

    print(
        f"  Bus ID      : "
        f"{config.bus_id}"
    )

    print(
        f"  Device ID   : "
        f"{config.device_id}"
    )

    print(
        f"  Camera ID   : "
        f"{config.camera_id}"
    )

    print(
        "\nBackend:"
    )

    print(
        f"  Enabled     : "
        f"{config.backend_enabled}"
    )

    print(
        f"  URL         : "
        f"{config.backend_url}"
    )

    print(
        f"  Timeout     : "
        f"{config.backend_timeout}"
    )

    print(
        "\nSynchronization:"
    )

    print(
        f"  Enabled     : "
        f"{config.sync_enabled}"
    )

    print(
        f"  Interval    : "
        f"{config.sync_interval}s"
    )

    print(
        f"  Batch size  : "
        f"{config.sync_batch_size}"
    )

    print(
        "\nConfiguration test passed."
    )


if __name__ == "__main__":
    main()