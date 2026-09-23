from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import numpy as np


class TrackLifecycleState:
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    TEMPORARILY_LOST = "TEMPORARILY_LOST"
    EXITED = "EXITED"


@dataclass
class VehicleTrajectory:
    """Historical tracking and surveillance state per vehicle."""
    track_id: int
    state: str = TrackLifecycleState.NEW
    centroids: List[Tuple[float, float, float]] = field(default_factory=list)  # (x, y, timestamp_sec)
    bboxes: List[List[int]] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    speeds_px_sec: List[float] = field(default_factory=list)
    lane_swerves: int = 0
    last_heading_rad: Optional[float] = None
    frames_tracked: int = 0
    missing_frames: int = 0
    last_seen_frame: int = 0
    anpr_triggered_count: int = 0

    def add_point(self, cx: float, cy: float, bbox: List[int], timestamp_sec: float, frame_number: int) -> None:
        self.centroids.append((cx, cy, timestamp_sec))
        self.bboxes.append(bbox)
        self.timestamps.append(timestamp_sec)
        self.frames_tracked += 1
        self.missing_frames = 0
        self.last_seen_frame = frame_number

        if self.frames_tracked == 1:
            self.state = TrackLifecycleState.NEW
        else:
            self.state = TrackLifecycleState.ACTIVE

        # Keep bounded history window (e.g. max 60 points)
        if len(self.centroids) > 60:
            self.centroids.pop(0)
            self.bboxes.pop(0)
            self.timestamps.pop(0)
            if self.speeds_px_sec:
                self.speeds_px_sec.pop(0)

        # Velocity estimation
        if len(self.centroids) >= 2:
            (x1, y1, t1) = self.centroids[-2]
            (x2, y2, t2) = self.centroids[-1]
            dt = t2 - t1
            if dt > 0.001:
                dist = float(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
                speed = dist / dt
                self.speeds_px_sec.append(speed)

                dx = x2 - x1
                dy = y2 - y1
                heading = float(np.arctan2(dy, dx))
                if self.last_heading_rad is not None:
                    diff_rad = abs(heading - self.last_heading_rad)
                    if diff_rad > 0.8:  # ~45 degree sudden deviation
                        self.lane_swerves += 1
                self.last_heading_rad = heading

    def mark_missing(self, max_missing_frames: int = 15) -> bool:
        """Increment missing frame count and update state. Returns True if EXITED."""
        self.missing_frames += 1
        if self.missing_frames > max_missing_frames:
            self.state = TrackLifecycleState.EXITED
            return True
        else:
            self.state = TrackLifecycleState.TEMPORARILY_LOST
            return False


class RashBehaviorAnalyzer:
    """
    Maintains per-vehicle trajectory buffers and extracts behavioral feature dicts
    to feed into the RashDrivingModel.
    """

    def __init__(self, history_window: int = 45, max_missing_frames: int = 20):
        self.history_window = history_window
        self.max_missing_frames = max_missing_frames
        self._trajectories: Dict[int, VehicleTrajectory] = {}
        self.total_unique_tracks_surveilled: int = 0

    def update_tracks(
        self,
        tracked_vehicles: List[Dict[str, Any]],
        video_time_seconds: float,
        frame_number: int = 0,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Update trajectory histories and return analysis features per track.
        """
        active_track_ids = set()
        features_by_track: Dict[int, Dict[str, Any]] = {}

        for vehicle in tracked_vehicles:
            track_id = vehicle.get("track_id")
            if track_id is None:
                continue

            active_track_ids.add(track_id)
            raw_bbox = vehicle.get("bbox")
            if isinstance(raw_bbox, dict):
                bbox_list = [
                    int(raw_bbox.get("xmin", 0)),
                    int(raw_bbox.get("ymin", 0)),
                    int(raw_bbox.get("xmax", 0)),
                    int(raw_bbox.get("ymax", 0)),
                ]
            elif isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) == 4:
                bbox_list = [int(x) for x in raw_bbox]
            else:
                bbox_list = [0, 0, 0, 0]

            centroid = vehicle.get("centroid")
            if centroid and len(centroid) >= 2:
                cx, cy = float(centroid[0]), float(centroid[1])
            else:
                cx = float((bbox_list[0] + bbox_list[2]) / 2.0)
                cy = float((bbox_list[1] + bbox_list[3]) / 2.0)

            if track_id not in self._trajectories:
                self._trajectories[track_id] = VehicleTrajectory(track_id=track_id)
                self.total_unique_tracks_surveilled += 1

            traj = self._trajectories[track_id]
            traj.add_point(cx, cy, bbox_list, video_time_seconds, frame_number)

            avg_speed = float(np.mean(traj.speeds_px_sec)) if traj.speeds_px_sec else 0.0
            max_speed = float(np.max(traj.speeds_px_sec)) if traj.speeds_px_sec else 0.0

            features_by_track[track_id] = {
                "track_id": track_id,
                "state": traj.state,
                "bbox": bbox_list,
                "frames_tracked": traj.frames_tracked,
                "speed_px_per_sec": avg_speed,
                "max_speed_px_sec": max_speed,
                "lane_swerves": traj.lane_swerves,
                "trajectory": list(traj.centroids),
                "wrong_way": False,
            }

        # Lifecycle update for missing / exited tracks
        stale_ids = []
        for tid, traj in list(self._trajectories.items()):
            if tid not in active_track_ids:
                is_exited = traj.mark_missing(self.max_missing_frames)
                if is_exited:
                    stale_ids.append(tid)

        # Clean up exited tracks
        for tid in stale_ids:
            del self._trajectories[tid]

        return features_by_track

    def get_track(self, track_id: int) -> Optional[VehicleTrajectory]:
        return self._trajectories.get(track_id)

    def get_active_track_count(self) -> int:
        return sum(1 for t in self._trajectories.values() if t.state in {TrackLifecycleState.NEW, TrackLifecycleState.ACTIVE})
