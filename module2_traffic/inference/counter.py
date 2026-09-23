from typing import Dict, Set, Optional, Tuple

from shared.config import Config


class VehicleCounter:
    """
    Virtual line-crossing vehicle counter.

    Supports directional counting:
    - direction_a: downward / incoming
    - direction_b: upward / outgoing

    Maintains class-wise breakdown for Indian road vehicles.
    Prevents duplicate counts of the same vehicle track.
    """

    # These class names must match the trained Indian vehicle YOLO model.
    VEHICLE_CLASSES = [
        "ambulance",
        "army vehicle",
        "auto rickshaw",
        "bicycle",
        "bus",
        "car",
        "garbagevan",
        "human hauler",
        "minibus",
        "minivan",
        "motorbike",
        "pickup",
        "policecar",
        "rickshaw",
        "scooter",
        "suv",
        "taxi",
        "three wheelers -cng-",
        "truck",
        "van",
        "wheelbarrow",
    ]

    def __init__(
        self,
        line_ratio: Optional[float] = None,
        direction_enabled: Optional[bool] = None,
    ):
        config = Config()

        self.line_ratio = float(
            line_ratio
            if line_ratio is not None
            else config.traffic_counting_line_position
        )

        self.direction_enabled = bool(
            direction_enabled
            if direction_enabled is not None
            else config.traffic_counting_direction_enabled
        )

        # Total counts by vehicle class.
        # All keys are normalized to lowercase.
        self.class_counts: Dict[str, int] = {
            class_name: 0
            for class_name in self.VEHICLE_CLASSES
        }

        # Directional counts.
        self.directional_counts: Dict[str, int] = {
            "direction_a": 0,
            "direction_b": 0,
        }

        # Track IDs that have already crossed the counting line.
        self.counted_tracks: Set[int] = set()

        # Previous centroid for every tracked vehicle.
        # track_id -> (cx, cy)
        self.prev_centroids: Dict[int, Tuple[float, float]] = {}

    @property
    def total_count(self) -> int:
        """
        Return the total number of vehicles counted.
        """
        return sum(self.class_counts.values())

    @staticmethod
    def _normalize_class_name(class_name: str) -> str:
        """
        Normalize model class names.

        This prevents duplicate categories caused by differences
        in capitalization or surrounding whitespace.
        """
        return str(class_name).strip().lower()

    def update(
        self,
        tracked_detections: list,
        frame_height: int,
    ) -> Dict:
        """
        Evaluate tracked detections against the virtual counting line.

        Counting line:
            y = frame_height * line_ratio

        A vehicle is counted only once when its centroid crosses
        the virtual line.
        """

        line_y = frame_height * self.line_ratio
        newly_counted = []

        for det in tracked_detections:

            track_id = det.get("track_id")

            if track_id is None:
                continue

            # Only confirmed tracks are eligible for counting.
            if not det.get("confirmed", True):
                continue

            centroid = det.get("centroid")

            # Calculate centroid from bounding box if necessary.
            if centroid is None:
                bbox = det["bbox"]

                centroid = (
                    (bbox["xmin"] + bbox["xmax"]) / 2.0,
                    (bbox["ymin"] + bbox["ymax"]) / 2.0,
                )

            cx, cy = centroid

            # Normalize class name to avoid duplicate keys.
            class_name = self._normalize_class_name(
                det.get("class_name", "car")
            )

            # If the detector returns an unexpected class,
            # keep the counter robust instead of crashing.
            if class_name not in self.class_counts:
                self.class_counts[class_name] = 0

            # Check whether this vehicle existed in the previous frame.
            if track_id in self.prev_centroids:

                prev_cx, prev_cy = self.prev_centroids[track_id]

                # Do not count the same tracked vehicle twice.
                if track_id not in self.counted_tracks:

                    crossed = False
                    direction = "direction_a"

                    # Downward crossing.
                    if prev_cy < line_y and cy >= line_y:

                        crossed = True
                        direction = "direction_a"

                    # Upward crossing.
                    elif prev_cy > line_y and cy <= line_y:

                        crossed = True
                        direction = "direction_b"

                    if crossed:

                        # Mark vehicle as permanently counted.
                        self.counted_tracks.add(track_id)

                        # Increase class count.
                        self.class_counts[class_name] += 1

                        # Increase directional count only if enabled.
                        if self.direction_enabled:
                            self.directional_counts[direction] += 1

                        newly_counted.append(
                            {
                                "track_id": track_id,
                                "class_name": class_name,
                                "direction": (
                                    direction
                                    if self.direction_enabled
                                    else None
                                ),
                                "centroid": (cx, cy),
                            }
                        )

            # Store current centroid for the next frame.
            self.prev_centroids[track_id] = (cx, cy)

        # Cleanup stale centroid memory if it becomes too large.
        current_track_ids = {
            d["track_id"]
            for d in tracked_detections
            if "track_id" in d and d["track_id"] is not None
        }

        if len(self.prev_centroids) > 500:

            self.prev_centroids = {
                track_id: centroid
                for track_id, centroid in self.prev_centroids.items()
                if track_id in current_track_ids
                or track_id in self.counted_tracks
            }

        return {
            "total_count": self.total_count,
            "class_counts": dict(self.class_counts),
            "directional_counts": dict(self.directional_counts),
            "newly_counted": newly_counted,
        }


def main():
    """
    Basic tests for the VehicleCounter.
    """

    print("=" * 60)
    print("VEHICLE COUNTER TEST")
    print("=" * 60)

    counter = VehicleCounter(line_ratio=0.5)

    # Frame height = 100.
    # Counting line = y = 50.
    frame_height = 100

    # --------------------------------------------------------
    # TEST 1: Car starts above the line.
    # --------------------------------------------------------

    d1 = [
        {
            "track_id": 1,
            "class_name": "car",
            "confirmed": True,
            "centroid": (50, 40),
        }
    ]

    counter.update(d1, frame_height)

    assert counter.total_count == 0

    # --------------------------------------------------------
    # TEST 2: Car crosses downward.
    # --------------------------------------------------------

    d2 = [
        {
            "track_id": 1,
            "class_name": "car",
            "confirmed": True,
            "centroid": (50, 60),
        }
    ]

    result = counter.update(d2, frame_height)

    assert counter.total_count == 1
    assert counter.class_counts["car"] == 1
    assert counter.directional_counts["direction_a"] == 1
    assert len(result["newly_counted"]) == 1

    # --------------------------------------------------------
    # TEST 3: Same car continues moving.
    # Must not be counted again.
    # --------------------------------------------------------

    d3 = [
        {
            "track_id": 1,
            "class_name": "car",
            "confirmed": True,
            "centroid": (50, 70),
        }
    ]

    counter.update(d3, frame_height)

    assert counter.total_count == 1

    # --------------------------------------------------------
    # TEST 4: Auto rickshaw crosses upward.
    # --------------------------------------------------------

    d4 = [
        {
            "track_id": 2,
            "class_name": "auto rickshaw",
            "confirmed": True,
            "centroid": (60, 70),
        }
    ]

    counter.update(d4, frame_height)

    d5 = [
        {
            "track_id": 2,
            "class_name": "auto rickshaw",
            "confirmed": True,
            "centroid": (60, 40),
        }
    ]

    counter.update(d5, frame_height)

    assert counter.total_count == 2
    assert counter.class_counts["auto rickshaw"] == 1
    assert counter.directional_counts["direction_b"] == 1

    # --------------------------------------------------------
    # TEST 5: CNG class normalization.
    # Model may theoretically return different capitalization.
    # --------------------------------------------------------

    d6 = [
        {
            "track_id": 3,
            "class_name": "three wheelers -CNG-",
            "confirmed": True,
            "centroid": (70, 40),
        }
    ]

    counter.update(d6, frame_height)

    d7 = [
        {
            "track_id": 3,
            "class_name": "three wheelers -CNG-",
            "confirmed": True,
            "centroid": (70, 60),
        }
    ]

    counter.update(d7, frame_height)

    assert counter.total_count == 3
    assert counter.class_counts["three wheelers -cng-"] == 1

    print("VehicleCounter test passed successfully.")
    print()
    print("Total counted:", counter.total_count)
    print("Class counts:", counter.class_counts)
    print("Directional counts:", counter.directional_counts)


if __name__ == "__main__":
    main()