from dataclasses import dataclass
from typing import Dict, List, Optional

from shared.config import Config


@dataclass
class Track:
    track_id: int
    bbox: Dict[str, float]
    last_frame: int
    hits: int = 1


class PotholeTracker:
    """
    Lightweight IoU-based tracker for pothole detections.

    Purpose:
        Prevent the same pothole from generating repeated alerts.

    Configuration is loaded from config/config.yaml unless
    explicit values are supplied.

    This remains intentionally lightweight and is not intended
    to replace a full multi-object tracking algorithm.
    """

    def __init__(
        self,
        iou_threshold: Optional[float] = None,
        max_missing_frames: Optional[int] = None,
        confirmation_hits: Optional[int] = None,
    ):

        config = Config()

        # ----------------------------------------------------
        # Tracker configuration
        # ----------------------------------------------------

        if iou_threshold is None:
            iou_threshold = (
                config.tracker_iou_threshold
            )

        if max_missing_frames is None:
            max_missing_frames = (
                config.tracker_max_missing_frames
            )

        if confirmation_hits is None:
            confirmation_hits = (
                config.tracker_confirmation_hits
            )

        self.iou_threshold = float(
            iou_threshold
        )

        self.max_missing_frames = int(
            max_missing_frames
        )

        self.confirmation_hits = int(
            confirmation_hits
        )

        # ----------------------------------------------------
        # Runtime state
        # ----------------------------------------------------

        self.tracks: List[Track] = []

        self.next_track_id = 1

    # ========================================================
    # IOU
    # ========================================================

    @staticmethod
    def _iou(
        box_a: Dict[str, float],
        box_b: Dict[str, float],
    ) -> float:

        ax1 = box_a["xmin"]
        ay1 = box_a["ymin"]
        ax2 = box_a["xmax"]
        ay2 = box_a["ymax"]

        bx1 = box_b["xmin"]
        by1 = box_b["ymin"]
        bx2 = box_b["xmax"]
        by2 = box_b["ymax"]

        intersection_x1 = max(
            ax1,
            bx1,
        )

        intersection_y1 = max(
            ay1,
            by1,
        )

        intersection_x2 = min(
            ax2,
            bx2,
        )

        intersection_y2 = min(
            ay2,
            by2,
        )

        intersection_width = max(
            0.0,
            intersection_x2
            - intersection_x1,
        )

        intersection_height = max(
            0.0,
            intersection_y2
            - intersection_y1,
        )

        intersection_area = (
            intersection_width
            * intersection_height
        )

        area_a = (
            max(
                0.0,
                ax2 - ax1,
            )
            *
            max(
                0.0,
                ay2 - ay1,
            )
        )

        area_b = (
            max(
                0.0,
                bx2 - bx1,
            )
            *
            max(
                0.0,
                by2 - by1,
            )
        )

        union_area = (
            area_a
            + area_b
            - intersection_area
        )

        if union_area <= 0:
            return 0.0

        return (
            intersection_area
            / union_area
        )

    # ========================================================
    # UPDATE TRACKS
    # ========================================================

    def update(
        self,
        detections: List[Dict],
        frame_number: int,
    ) -> List[Dict]:

        results = []

        matched_track_ids = set()

        # ----------------------------------------------------
        # Match detections to existing tracks
        # ----------------------------------------------------

        for detection in detections:

            bbox = detection["bbox"]

            best_track: Optional[Track] = None
            best_iou = 0.0

            for track in self.tracks:

                if (
                    track.track_id
                    in matched_track_ids
                ):
                    continue

                iou = self._iou(
                    bbox,
                    track.bbox,
                )

                if iou > best_iou:

                    best_iou = iou
                    best_track = track

            # ------------------------------------------------
            # Existing track matched
            # ------------------------------------------------

            if (
                best_track is not None
                and best_iou
                >= self.iou_threshold
            ):

                best_track.bbox = bbox

                best_track.last_frame = (
                    frame_number
                )

                best_track.hits += 1

                matched_track_ids.add(
                    best_track.track_id
                )

                detection_result = dict(
                    detection
                )

                detection_result[
                    "track_id"
                ] = best_track.track_id

                detection_result[
                    "track_hits"
                ] = best_track.hits

                detection_result[
                    "confirmed"
                ] = (
                    best_track.hits
                    >= self.confirmation_hits
                )

                detection_result[
                    "new_track"
                ] = False

                results.append(
                    detection_result
                )

            # ------------------------------------------------
            # New track
            # ------------------------------------------------

            else:

                track = Track(
                    track_id=(
                        self.next_track_id
                    ),
                    bbox=bbox,
                    last_frame=frame_number,
                )

                self.tracks.append(
                    track
                )

                self.next_track_id += 1

                matched_track_ids.add(
                    track.track_id
                )

                detection_result = dict(
                    detection
                )

                detection_result[
                    "track_id"
                ] = track.track_id

                detection_result[
                    "track_hits"
                ] = 1

                detection_result[
                    "confirmed"
                ] = (
                    self.confirmation_hits
                    <= 1
                )

                detection_result[
                    "new_track"
                ] = True

                results.append(
                    detection_result
                )

        # ----------------------------------------------------
        # Remove stale tracks
        # ----------------------------------------------------

        active_tracks = []

        for track in self.tracks:

            if (
                frame_number
                - track.last_frame
                <= self.max_missing_frames
            ):

                active_tracks.append(
                    track
                )

        self.tracks = active_tracks

        return results


def main():

    print("=" * 60)
    print("POTHOLE TRACKER CONFIGURATION TEST")
    print("=" * 60)

    tracker = PotholeTracker()

    print(
        "\nConfiguration:"
    )

    print(
        f"  IoU threshold      : "
        f"{tracker.iou_threshold}"
    )

    print(
        f"  Confirmation hits  : "
        f"{tracker.confirmation_hits}"
    )

    print(
        f"  Max missing frames : "
        f"{tracker.max_missing_frames}"
    )

    # --------------------------------------------------------
    # Test same pothole across three frames
    # --------------------------------------------------------

    detections_frame_1 = [
        {
            "confidence": 0.70,
            "bbox": {
                "xmin": 100,
                "ymin": 200,
                "xmax": 200,
                "ymax": 300,
            },
        }
    ]

    detections_frame_2 = [
        {
            "confidence": 0.75,
            "bbox": {
                "xmin": 105,
                "ymin": 205,
                "xmax": 205,
                "ymax": 305,
            },
        }
    ]

    detections_frame_3 = [
        {
            "confidence": 0.80,
            "bbox": {
                "xmin": 110,
                "ymin": 210,
                "xmax": 210,
                "ymax": 310,
            },
        }
    ]

    result_1 = tracker.update(
        detections_frame_1,
        frame_number=1,
    )

    result_2 = tracker.update(
        detections_frame_2,
        frame_number=2,
    )

    result_3 = tracker.update(
        detections_frame_3,
        frame_number=3,
    )

    print(
        "\nFrame 1:"
    )

    print(
        result_1
    )

    print(
        "\nFrame 2:"
    )

    print(
        result_2
    )

    print(
        "\nFrame 3:"
    )

    print(
        result_3
    )

    # --------------------------------------------------------
    # Verify confirmation
    # --------------------------------------------------------

    assert result_1[0]["confirmed"] is False

    assert result_2[0]["confirmed"] is True

    assert result_3[0]["confirmed"] is True

    assert (
        result_1[0]["track_id"]
        == result_2[0]["track_id"]
        == result_3[0]["track_id"]
    )

    print(
        "\nTracker configuration test passed."
    )


if __name__ == "__main__":

    main()