from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

from shared.config import Config


@dataclass
class VehicleTrack:
    track_id: int
    class_name: str
    bbox: Dict[str, float]
    confidence: float
    last_seen_frame: int
    hits: int = 1
    trajectory: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def centroid(self) -> Tuple[float, float]:
        cx = (self.bbox["xmin"] + self.bbox["xmax"]) / 2.0
        cy = (self.bbox["ymin"] + self.bbox["ymax"]) / 2.0
        return cx, cy


class VehicleTracker:
    """
    Multi-vehicle tracker using IoU and centroid distance.

    Improvements over the previous tracker:
    - Matches only compatible vehicle classes.
    - Uses centroid distance when IoU becomes weak.
    - Prevents multiple detections from matching one track.
    - Maintains track IDs more reliably across frame movement.
    - Helps reduce duplicate line-crossing counts.
    """

    def __init__(
        self,
        iou_threshold: Optional[float] = None,
        max_missing_frames: Optional[int] = None,
        confirmation_hits: Optional[int] = None,
        max_centroid_distance: float = 120.0,
    ):
        config = Config()

        self.iou_threshold = float(
            iou_threshold
            if iou_threshold is not None
            else config.traffic_tracker_iou
        )

        self.max_missing_frames = int(
            max_missing_frames
            if max_missing_frames is not None
            else config.traffic_tracker_max_missing
        )

        self.confirmation_hits = int(
            confirmation_hits
            if confirmation_hits is not None
            else config.traffic_tracker_confirmation_hits
        )

        # Maximum allowed centroid movement for fallback matching.
        self.max_centroid_distance = float(max_centroid_distance)

        self.tracks: List[VehicleTrack] = []
        self.next_track_id: int = 1

    @staticmethod
    def _iou(
        box_a: Dict[str, float],
        box_b: Dict[str, float],
    ) -> float:
        """
        Calculate Intersection over Union between two bounding boxes.
        """

        ax1 = box_a["xmin"]
        ay1 = box_a["ymin"]
        ax2 = box_a["xmax"]
        ay2 = box_a["ymax"]

        bx1 = box_b["xmin"]
        by1 = box_b["ymin"]
        bx2 = box_b["xmax"]
        by2 = box_b["ymax"]

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)

        intersection = iw * ih

        area_a = (
            max(0.0, ax2 - ax1)
            * max(0.0, ay2 - ay1)
        )

        area_b = (
            max(0.0, bx2 - bx1)
            * max(0.0, by2 - by1)
        )

        union = area_a + area_b - intersection

        if union <= 0.0:
            return 0.0

        return intersection / union

    @staticmethod
    def _centroid_from_bbox(
        bbox: Dict[str, float],
    ) -> Tuple[float, float]:
        """
        Calculate the center point of a bounding box.
        """

        cx = (
            bbox["xmin"]
            + bbox["xmax"]
        ) / 2.0

        cy = (
            bbox["ymin"]
            + bbox["ymax"]
        ) / 2.0

        return cx, cy

    @staticmethod
    def _centroid_distance(
        centroid_a: Tuple[float, float],
        centroid_b: Tuple[float, float],
    ) -> float:
        """
        Calculate Euclidean distance between two centroids.
        """

        dx = centroid_a[0] - centroid_b[0]
        dy = centroid_a[1] - centroid_b[1]

        return math.sqrt(
            dx * dx
            + dy * dy
        )

    @staticmethod
    def _normalize_class_name(
        class_name: str,
    ) -> str:
        """
        Normalize vehicle class names.
        """

        return str(class_name).strip().lower()

    def _classes_compatible(
        self,
        track_class: str,
        detection_class: str,
    ) -> bool:
        """
        Check whether two classes are compatible for tracking.

        We normally require an exact class match.

        Some related classes are allowed because the detector can
        occasionally switch between similar Indian vehicle categories.
        """

        track_class = self._normalize_class_name(track_class)
        detection_class = self._normalize_class_name(detection_class)

        if track_class == detection_class:
            return True

        # Auto-rickshaw related categories.
        auto_classes = {
            "auto rickshaw",
            "rickshaw",
            "three wheelers -cng-",
            "three wheelers -CNG-".lower(),
        }

        if (
            track_class in auto_classes
            and detection_class in auto_classes
        ):
            return True

        # Motorcycle and scooter are visually similar and may switch.
        two_wheeler_classes = {
            "motorbike",
            "motorcycle",
            "scooter",
        }

        if (
            track_class in two_wheeler_classes
            and detection_class in two_wheeler_classes
        ):
            return True

        # Car-related categories.
        car_classes = {
            "car",
            "suv",
            "taxi",
        }

        if (
            track_class in car_classes
            and detection_class in car_classes
        ):
            return True

        return False

    def _match_detection_to_track(
        self,
        bbox: Dict[str, float],
        class_name: str,
        matched_track_ids: set,
    ) -> Optional[VehicleTrack]:
        """
        Find the best available track for a detection.

        Matching priority:
        1. Same or compatible vehicle class.
        2. Strong IoU overlap.
        3. Centroid distance fallback.
        """

        detection_centroid = self._centroid_from_bbox(
            bbox
        )

        best_track = None
        best_score = -1.0

        for track in self.tracks:

            # A track can only be matched once per frame.
            if track.track_id in matched_track_ids:
                continue

            # Prevent unrelated vehicle classes from stealing tracks.
            if not self._classes_compatible(
                track.class_name,
                class_name,
            ):
                continue

            track_centroid = track.centroid

            iou = self._iou(
                bbox,
                track.bbox,
            )

            distance = self._centroid_distance(
                detection_centroid,
                track_centroid,
            )

            # Reject tracks that are both far away and have no overlap.
            if (
                iou < self.iou_threshold
                and distance > self.max_centroid_distance
            ):
                continue

            # Normalize distance.
            distance_score = max(
                0.0,
                1.0 - (
                    distance
                    / self.max_centroid_distance
                ),
            )

            # Combined score.
            # IoU is primary, centroid distance provides fallback.
            score = (
                0.65 * iou
                + 0.35 * distance_score
            )

            # Small preference for exact class matches.
            if (
                self._normalize_class_name(
                    track.class_name
                )
                ==
                self._normalize_class_name(
                    class_name
                )
            ):
                score += 0.10

            if score > best_score:
                best_score = score
                best_track = track

        return best_track

    def update(
        self,
        detections: List[Dict],
        frame_number: int,
    ) -> List[Dict]:
        """
        Update vehicle tracks with new detections.

        Returns augmented detection dictionaries containing:

        - track_id
        - track_hits
        - confirmed
        - new_track
        - centroid
        """

        results = []

        # Tracks already matched during this frame.
        matched_track_ids = set()

        for det in detections:

            bbox = det["bbox"]

            class_name = self._normalize_class_name(
                det.get(
                    "class_name",
                    "car",
                )
            )

            confidence = float(
                det.get(
                    "confidence",
                    0.0,
                )
            )

            best_track = self._match_detection_to_track(
                bbox=bbox,
                class_name=class_name,
                matched_track_ids=matched_track_ids,
            )

            # ==================================================
            # EXISTING TRACK MATCH
            # ==================================================

            if best_track is not None:

                best_track.bbox = bbox

                best_track.class_name = class_name

                best_track.confidence = confidence

                best_track.last_seen_frame = frame_number

                best_track.hits += 1

                current_centroid = best_track.centroid

                best_track.trajectory.append(
                    current_centroid
                )

                matched_track_ids.add(
                    best_track.track_id
                )

                result = dict(det)

                result["class_name"] = class_name

                result["track_id"] = (
                    best_track.track_id
                )

                result["track_hits"] = (
                    best_track.hits
                )

                result["confirmed"] = (
                    best_track.hits
                    >= self.confirmation_hits
                )

                result["new_track"] = False

                result["centroid"] = (
                    current_centroid
                )

                results.append(
                    result
                )

            # ==================================================
            # NEW TRACK
            # ==================================================

            else:

                new_track = VehicleTrack(

                    track_id=self.next_track_id,

                    class_name=class_name,

                    bbox=bbox,

                    confidence=confidence,

                    last_seen_frame=frame_number,

                    hits=1,

                    trajectory=[],
                )

                new_track.trajectory.append(
                    new_track.centroid
                )

                self.tracks.append(
                    new_track
                )

                matched_track_ids.add(
                    new_track.track_id
                )

                self.next_track_id += 1

                result = dict(det)

                result["class_name"] = class_name

                result["track_id"] = (
                    new_track.track_id
                )

                result["track_hits"] = 1

                result["confirmed"] = (
                    self.confirmation_hits <= 1
                )

                result["new_track"] = True

                result["centroid"] = (
                    new_track.centroid
                )

                results.append(
                    result
                )

        # ======================================================
        # REMOVE STALE TRACKS
        # ======================================================

        self.tracks = [

            track

            for track in self.tracks

            if (
                frame_number
                - track.last_seen_frame
            )
            <= self.max_missing_frames
        ]

        return results


def main():

    print("=" * 60)

    print("VEHICLE TRACKER TEST")

    print("=" * 60)

    tracker = VehicleTracker(

        iou_threshold=0.30,

        confirmation_hits=2,

        max_missing_frames=10,

        max_centroid_distance=120.0,
    )

    # First frame.
    f1 = [
        {
            "class_name": "car",

            "confidence": 0.80,

            "bbox": {
                "xmin": 10,
                "ymin": 10,
                "xmax": 50,
                "ymax": 50,
            },
        }
    ]

    # Vehicle moves slightly.
    f2 = [
        {
            "class_name": "car",

            "confidence": 0.82,

            "bbox": {
                "xmin": 15,
                "ymin": 12,
                "xmax": 55,
                "ymax": 52,
            },
        }
    ]

    r1 = tracker.update(
        f1,
        1,
    )

    r2 = tracker.update(
        f2,
        2,
    )

    assert (
        r1[0]["track_id"]
        ==
        r2[0]["track_id"]
    )

    assert (
        r1[0]["confirmed"]
        is False
    )

    assert (
        r2[0]["confirmed"]
        is True
    )

    print(
        "VehicleTracker test passed successfully."
    )

    print(
        "Track ID:",
        r2[0]["track_id"],
    )

    print(
        "Track hits:",
        r2[0]["track_hits"],
    )


if __name__ == "__main__":
    main()