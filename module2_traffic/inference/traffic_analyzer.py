from typing import Dict, Any, Optional
from shared.config import Config


class TrafficAnalyzer:
    """
    Evaluates traffic conditions and congestion levels.
    Converts active vehicles, counted flow, and occupancy into a deterministic
    traffic state: LOW, MEDIUM, HIGH, CRITICAL.

    All thresholds are read from config.yaml.
    """

    def __init__(
        self,
        low_threshold: Optional[int] = None,
        medium_threshold: Optional[int] = None,
        high_threshold: Optional[int] = None,
        observation_interval: Optional[int] = None,
    ):
        config = Config()
        self.low_threshold = int(low_threshold if low_threshold is not None else config.traffic_low_threshold)
        self.medium_threshold = int(medium_threshold if medium_threshold is not None else config.traffic_medium_threshold)
        self.high_threshold = int(high_threshold if high_threshold is not None else config.traffic_high_threshold)
        self.observation_interval = int(observation_interval if observation_interval is not None else config.traffic_observation_interval)

    def analyze(
        self,
        active_vehicle_count: int,
        total_counted: int,
        class_counts: Dict[str, int],
        directional_counts: Dict[str, int],
        frame_width: int,
        frame_height: int,
        detections: list,
    ) -> Dict[str, Any]:
        """
        Compute traffic state, density, and congestion metrics.
        """
        # Occupancy approximation: total area of vehicle bboxes / frame area
        frame_area = max(1.0, float(frame_width * frame_height))
        total_vehicle_area = 0.0
        for det in detections:
            bbox = det.get("bbox", {})
            w = max(0.0, bbox.get("xmax", 0) - bbox.get("xmin", 0))
            h = max(0.0, bbox.get("ymax", 0) - bbox.get("ymin", 0))
            total_vehicle_area += (w * h)

        occupancy_ratio = min(1.0, total_vehicle_area / frame_area)
        occupancy_pct = round(occupancy_ratio * 100.0, 1)

        # Congestion classification based on active vehicles and occupancy
        # Low: active < low_threshold
        # Medium: low_threshold <= active < medium_threshold
        # High: medium_threshold <= active < high_threshold
        # Critical: active >= high_threshold or occupancy_pct > 65%
        if active_vehicle_count >= self.high_threshold or occupancy_pct >= 65.0:
            congestion_level = "critical"
            density = "very_high"
            severity = "critical"
        elif active_vehicle_count >= self.medium_threshold or occupancy_pct >= 40.0:
            congestion_level = "high"
            density = "high"
            severity = "high"
        elif active_vehicle_count >= self.low_threshold or occupancy_pct >= 20.0:
            congestion_level = "medium"
            density = "medium"
            severity = "medium"
        else:
            congestion_level = "low"
            density = "low"
            severity = "low"

        return {
            "active_vehicle_count": active_vehicle_count,
            "total_vehicle_count": total_counted,
            "vehicle_classes": dict(class_counts),
            "directional_counts": dict(directional_counts),
            "congestion_level": congestion_level,
            "density": density,
            "severity": severity,
            "occupancy_pct": occupancy_pct,
        }


def main():
    print("=" * 60)
    print("TRAFFIC ANALYZER TEST")
    print("=" * 60)
    analyzer = TrafficAnalyzer(low_threshold=5, medium_threshold=12, high_threshold=20)
    res_low = analyzer.analyze(2, 5, {"car": 5}, {}, 640, 480, [])
    assert res_low["congestion_level"] == "low"

    res_med = analyzer.analyze(8, 10, {"car": 10}, {}, 640, 480, [])
    assert res_med["congestion_level"] == "medium"

    res_high = analyzer.analyze(15, 20, {"car": 20}, {}, 640, 480, [])
    assert res_high["congestion_level"] == "high"

    res_crit = analyzer.analyze(25, 30, {"car": 30}, {}, 640, 480, [])
    assert res_crit["congestion_level"] == "critical"

    print("TrafficAnalyzer test passed successfully.")


if __name__ == "__main__":
    main()
