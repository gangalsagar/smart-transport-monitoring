#!/usr/bin/env python3
"""
Module 3: Temporal Track-Plate Aggregator
=========================================
Associates license plate detections with active multi-vehicle tracks.
Aggregates temporal OCR predictions per vehicle to produce a high-confidence consensus plate.
"""

from typing import Dict, List, Optional, Tuple, Any
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import numpy as np

@dataclass
class TrackPlateHistory:
    track_id: int
    readings: List[str] = field(default_factory=list)
    confidences: List[float] = field(default_factory=list)
    last_bbox: Optional[Tuple[int, int, int, int]] = None
    last_frame_number: int = 0

class TrackPlateAggregator:
    """
    Maintains persistent track-to-plate mappings.
    Prevents duplicate OCR passes on every frame and provides majority-voting
    temporal consensus across moving vehicle track observations.
    """

    def __init__(
        self,
        history_window: int = 15,
        min_consensus_votes: int = 2,
        ocr_interval_frames: int = 3
    ):
        self.history_window = history_window
        self.min_consensus_votes = min_consensus_votes
        self.ocr_interval_frames = ocr_interval_frames
        self.track_histories: Dict[int, TrackPlateHistory] = {}

    def should_process_track(self, track_id: int, current_frame: int) -> bool:
        """Rate-limit OCR passes per track to conserve edge compute."""
        if track_id not in self.track_histories:
            return True
        hist = self.track_histories[track_id]
        return (current_frame - hist.last_frame_number) >= self.ocr_interval_frames

    def add_reading(
        self,
        track_id: int,
        plate_text: Optional[str],
        confidence: float,
        plate_bbox: Optional[Tuple[int, int, int, int]],
        frame_number: int
    ):
        """Record an ANPR reading for a specific vehicle track."""
        if track_id not in self.track_histories:
            self.track_histories[track_id] = TrackPlateHistory(track_id=track_id)

        hist = self.track_histories[track_id]
        hist.last_frame_number = frame_number
        if plate_bbox:
            hist.last_bbox = plate_bbox

        if plate_text and len(plate_text) >= 4:
            hist.readings.append(plate_text)
            hist.confidences.append(confidence)

            # Enforce sliding history window
            if len(hist.readings) > self.history_window:
                hist.readings.pop(0)
                hist.confidences.pop(0)

    def get_consensus_plate(self, track_id: int) -> Tuple[Optional[str], float, str]:
        """
        Get the most reliable plate string for a track using temporal voting.
        
        Returns:
            (plate_text, confidence, status)
        """
        if track_id not in self.track_histories:
            return None, 0.0, "unavailable"

        hist = self.track_histories[track_id]
        if not hist.readings:
            return None, 0.0, "detected_unreadable" if hist.last_bbox else "unavailable"

        # 1. Majority Voting
        counts = Counter(hist.readings)
        most_common_plate, vote_count = counts.most_common(1)[0]

        # 2. Confidence weighted score
        matching_confidences = [
            conf for plate, conf in zip(hist.readings, hist.confidences)
            if plate == most_common_plate
        ]
        avg_conf = float(np.mean(matching_confidences)) if matching_confidences else 0.70

        status = "recognized" if vote_count >= self.min_consensus_votes else "provisional"
        return most_common_plate, round(avg_conf, 3), status

    def cleanup_old_tracks(self, active_track_ids: List[int]):
        """Remove tracks that are no longer active to prevent memory growth."""
        active_set = set(active_track_ids)
        to_delete = [t_id for t_id in self.track_histories if t_id not in active_set]
        for t_id in to_delete:
            del self.track_histories[t_id]
