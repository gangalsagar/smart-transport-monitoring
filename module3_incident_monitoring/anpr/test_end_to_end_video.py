#!/usr/bin/env python3
"""
Module 3: Real End-to-End ANPR Video Pipeline Test
==================================================
Performs full-stream video ANPR processing:
1. Locates test video in module3_incident_anpr/test_videos or module3_incident_anpr/test video
2. Runs existing Module 2 YOLO VehicleDetector
3. Runs existing Module 2 VehicleTracker with Track ID persistence
4. Crops vehicle regions
5. Runs Stage 1 PlateDetector
6. Runs Stage 2 CRNN Baseline OCR (best_ocr_model.pt)
7. Aggregates multi-frame OCR via TrackPlateAggregator (temporal majority voting)
8. Generates an annotated output video with bounding boxes & recognized plates
9. Exports structured execution telemetry to module3_incident_anpr/results/
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
import torch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import existing vehicle detection and tracking
from module2_traffic.inference.detector import VehicleDetector
from module2_traffic.inference.tracker import VehicleTracker

# Import verified ANPR components
from module3_incident_anpr.inference.plate_detector import PlateDetector
from module3_incident_anpr.inference.anpr_engine import ANPREngine
from module3_incident_anpr.inference.track_plate_aggregator import TrackPlateAggregator

def find_test_video(search_dirs: List[Path]) -> Optional[Path]:
    """Search for test video files across candidate directories."""
    extensions = [".mp4", ".avi", ".mkv", ".mov"]
    for s_dir in search_dirs:
        if s_dir.exists():
            for ext in extensions:
                found = list(s_dir.glob(f"*{ext}"))
                if found:
                    return found[0]
    return None

def run_end_to_end_test(
    video_path: Optional[str] = None,
    checkpoint_path: str = "module3_incident_anpr/ocr_checkpoints/best_ocr_model.pt",
    output_dir: str = "module3_incident_anpr/output_videos",
    results_dir: str = "module3_incident_anpr/results",
    max_frames: Optional[int] = None,
    save_video: bool = True
):
    print("=" * 80)
    print("MODULE 3 ANPR: REAL END-TO-END VIDEO INTEGRATION TEST")
    print("=" * 80)

    # 1. Resolve Test Video
    candidate_dirs = [
        PROJECT_ROOT / "module3_incident_anpr" / "test video",
        PROJECT_ROOT / "module3_incident_anpr" / "test_videos",
        PROJECT_ROOT / "module3_incident_anpr" / "data" / "test_videos",
        PROJECT_ROOT / "data" / "videos",
    ]

    if video_path:
        input_video_path = Path(video_path)
    else:
        input_video_path = find_test_video(candidate_dirs)

    if not input_video_path or not input_video_path.exists():
        print(f"[-] ERROR: No test video found. Searched paths:")
        for d in candidate_dirs:
            print(f"    - {d}")
        sys.exit(1)

    # 2. Check OCR Checkpoint
    checkpoint_file = PROJECT_ROOT / checkpoint_path
    if not checkpoint_file.exists():
        print(f"[-] ERROR: OCR Checkpoint not found at {checkpoint_file}")
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # 3. Open Video Stream
    cap = cv2.VideoCapture(str(input_video_path))
    if not cap.isOpened():
        print(f"[-] ERROR: Failed to open video file at {input_video_path}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[+] Input Video:       {input_video_path}")
    print(f"[+] Resolution:        {width} x {height}")
    print(f"[+] Video FPS:         {fps:.2f}")
    print(f"[+] Total Video Frames:{total_frames}")
    print(f"[+] Compute Device:    {device}")
    print(f"[+] OCR Checkpoint:    {checkpoint_file}")
    print("=" * 80)

    # 4. Initialize Pipeline Components
    print("\n[+] Initializing Vehicle Detector (YOLO)...")
    detector = VehicleDetector(confidence=0.35)

    print("[+] Initializing Vehicle Tracker (IoU + Centroid)...")
    tracker = VehicleTracker(iou_threshold=0.30, max_missing_frames=25, confirmation_hits=2)

    print("[+] Initializing Unified ANPR Engine (Stage 1 PlateDetector + Stage 2 CRNN OCR)...")
    anpr_engine = ANPREngine(checkpoint_path=checkpoint_file, device=device)

    print("[+] Initializing Temporal Track-Plate Aggregator...")
    aggregator = TrackPlateAggregator(history_window=20, min_consensus_votes=2, ocr_interval_frames=3)

    # 5. Initialize Video Writer
    out_video_writer = None
    output_video_path = None
    if save_video:
        out_dir = PROJECT_ROOT / output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        output_video_path = out_dir / f"anpr_annotated_{input_video_path.stem}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out_video_writer = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))
        print(f"[+] Output Video Path: {output_video_path}")

    # Metrics Collection
    frame_count = 0
    total_vehicle_detections = 0
    unique_tracks_seen = set()
    ocr_attempts = 0
    plate_candidates_localized = 0
    ocr_recognized_count = 0
    frame_processing_latencies = []

    per_frame_records = []

    print("\n[+] Processing Video Stream...\n")
    start_time = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if max_frames and frame_count > max_frames:
            break

        f_t0 = time.perf_counter()

        # Step 1: Vehicle Detection
        raw_detections = detector.detect(frame)
        total_vehicle_detections += len(raw_detections)

        # Step 2: Vehicle Tracking
        tracked_vehicles = tracker.update(raw_detections, frame_number=frame_count)

        active_track_ids = []
        frame_track_records = []

        # Annotated frame buffer
        annotated_frame = frame.copy() if save_video else None

        for v in tracked_vehicles:
            track_id = v.get("track_id")
            active_track_ids.append(track_id)
            unique_tracks_seen.add(track_id)

            bbox = v.get("bbox", {})
            xmin = max(0, int(bbox.get("xmin", 0)))
            ymin = max(0, int(bbox.get("ymin", 0)))
            xmax = min(width, int(bbox.get("xmax", 0)))
            ymax = min(height, int(bbox.get("ymax", 0)))
            class_name = v.get("class_name", "vehicle")

            plate_str = None
            plate_conf = 0.0
            plate_status = "unavailable"
            plate_bbox_global = None

            # Step 3: Crop Vehicle & Run ANPR
            if (xmax > xmin + 20) and (ymax > ymin + 20):
                # Rate limit OCR passes per track
                if aggregator.should_process_track(track_id, frame_count):
                    vehicle_crop = frame[ymin:ymax, xmin:xmax]
                    
                    # Stage 1: Detect Plate within crop
                    plate_dets = anpr_engine.detector.detect(vehicle_crop)
                    if plate_dets:
                        plate_candidates_localized += 1
                        top_p = plate_dets[0]
                        p_xmin, p_ymin, p_xmax, p_ymax = top_p.bbox
                        plate_bbox_global = (
                            xmin + p_xmin,
                            ymin + p_ymin,
                            xmin + p_xmax,
                            ymin + p_ymax
                        )

                        # Stage 2: OCR Recognition
                        ocr_attempts += 1
                        plate_str, plate_conf = anpr_engine.recognize_crop(top_p.crop)
                        if plate_str:
                            ocr_recognized_count += 1
                            plate_status = "recognized"
                        else:
                            plate_status = "detected_unreadable"

                    # Step 4: Add to Temporal Aggregator
                    aggregator.add_reading(
                        track_id=track_id,
                        plate_text=plate_str,
                        confidence=plate_conf,
                        plate_bbox=plate_bbox_global,
                        frame_number=frame_count
                    )

            # Retrieve temporal consensus for track
            consensus_plate, consensus_conf, consensus_status = aggregator.get_consensus_plate(track_id)

            # Record track observation
            frame_track_records.append({
                "track_id": track_id,
                "class_name": class_name,
                "vehicle_bbox": [xmin, ymin, xmax, ymax],
                "current_plate": plate_str,
                "current_confidence": plate_conf,
                "consensus_plate": consensus_plate,
                "consensus_confidence": consensus_conf,
                "consensus_status": consensus_status
            })

            # Step 5: Visual Annotation
            if save_video and annotated_frame is not None:
                # Vehicle Bounding Box (Cyan)
                cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), (255, 200, 0), 2)
                
                # Vehicle Label Header
                display_label = f"ID:{track_id} {class_name.upper()}"
                cv2.putText(
                    annotated_frame, display_label, (xmin, max(20, ymin - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 2, cv2.LINE_AA
                )

                # Plate Box & Text Annotation (Green if consensus recognized, Yellow if provisional)
                if plate_bbox_global:
                    px1, py1, px2, py2 = plate_bbox_global
                    cv2.rectangle(annotated_frame, (px1, py1), (px2, py2), (0, 255, 0), 2)

                if consensus_plate:
                    plate_banner = f"PLATE: {consensus_plate} ({consensus_conf:.2f})"
                    box_color = (0, 255, 0) if consensus_status == "recognized" else (0, 255, 255)
                    
                    # Background text pill
                    (tw, th), _ = cv2.getTextSize(plate_banner, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(
                        annotated_frame,
                        (xmin, ymax + 5),
                        (xmin + tw + 10, ymax + th + 15),
                        (0, 0, 0),
                        -1
                    )
                    cv2.putText(
                        annotated_frame, plate_banner, (xmin + 5, ymax + th + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2, cv2.LINE_AA
                    )

        # Cleanup inactive tracks from aggregator
        aggregator.cleanup_old_tracks(active_track_ids)

        if save_video and out_video_writer is not None:
            # HUD Watermark
            hud_text = f"Frame: {frame_count:04d} | Active Tracks: {len(tracked_vehicles)} | OCR Passes: {ocr_attempts}"
            cv2.putText(annotated_frame, hud_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
            out_video_writer.write(annotated_frame)

        f_t1 = time.perf_counter()
        frame_processing_latencies.append((f_t1 - f_t0) * 1000.0)

        if frame_count % 25 == 0 or frame_count == total_frames:
            elapsed_sec = time.perf_counter() - start_time
            current_fps = frame_count / max(0.001, elapsed_sec)
            print(f"  Frame {frame_count:04d}/{total_frames} | Tracks: {len(tracked_vehicles)} | OCR Passed: {ocr_recognized_count} | Throughput: {current_fps:.1f} FPS")

    # Finalize Video Writer & Capture
    cap.release()
    if out_video_writer is not None:
        out_video_writer.release()

    total_elapsed = time.perf_counter() - start_time
    avg_fps = frame_count / max(0.001, total_elapsed)
    mean_latency_ms = float(np.mean(frame_processing_latencies)) if frame_processing_latencies else 0.0

    # Build Final Track Summary
    final_tracks_summary = {}
    for t_id in unique_tracks_seen:
        c_plate, c_conf, c_stat = aggregator.get_consensus_plate(t_id)
        final_tracks_summary[str(t_id)] = {
            "track_id": t_id,
            "final_plate_consensus": c_plate,
            "consensus_confidence": c_conf,
            "status": c_stat,
            "total_readings": len(aggregator.track_histories[t_id].readings) if t_id in aggregator.track_histories else 0
        }

    # Save JSON Results
    results_out_dir = PROJECT_ROOT / results_dir
    results_out_dir.mkdir(parents=True, exist_ok=True)
    results_json_path = results_out_dir / f"anpr_video_test_results_{input_video_path.stem}.json"

    report_payload = {
        "input_video": {
            "path": str(input_video_path),
            "resolution": f"{width}x{height}",
            "fps": fps,
            "total_frames_in_file": total_frames
        },
        "execution_summary": {
            "frames_processed": frame_count,
            "processing_duration_sec": round(total_elapsed, 2),
            "average_throughput_fps": round(avg_fps, 2),
            "mean_frame_latency_ms": round(mean_latency_ms, 2),
            "device": device,
            "ocr_checkpoint": str(checkpoint_file)
        },
        "pipeline_metrics": {
            "total_vehicle_detections": total_vehicle_detections,
            "unique_vehicle_tracks": len(unique_tracks_seen),
            "plate_candidates_localized": plate_candidates_localized,
            "ocr_inference_attempts": ocr_attempts,
            "ocr_successful_recognitions": ocr_recognized_count,
            "tracks_with_consensus_plate": sum(1 for t in final_tracks_summary.values() if t["final_plate_consensus"] is not None)
        },
        "tracks_summary": final_tracks_summary,
        "output_artifacts": {
            "annotated_video": str(output_video_path) if output_video_path else None,
            "results_json": str(results_json_path)
        }
    }

    with open(results_json_path, "w") as f:
        json.dump(report_payload, f, indent=2)

    print("\n" + "=" * 80)
    print("END-TO-END ANPR VIDEO TEST SUMMARY")
    print("=" * 80)
    print(f"Frames Processed:               {frame_count} / {total_frames}")
    print(f"Total Processing Time:          {total_elapsed:.2f} s")
    print(f"Average System Throughput:      {avg_fps:.2f} FPS")
    print(f"Mean Frame Latency:             {mean_latency_ms:.2f} ms")
    print(f"Total Vehicle Detections:       {total_vehicle_detections}")
    print(f"Unique Vehicle Tracks:          {len(unique_tracks_seen)}")
    print(f"Plate Candidates Localized:     {plate_candidates_localized}")
    print(f"OCR Inference Passes:           {ocr_attempts}")
    print(f"Successful OCR Extractions:     {ocr_recognized_count}")
    print(f"Tracks with Resolved Plate:     {sum(1 for t in final_tracks_summary.values() if t['final_plate_consensus'] is not None)}")
    if output_video_path:
        print(f"Annotated Video Saved:          {output_video_path}")
    print(f"Detailed Results Saved:         {results_json_path}")
    print("=" * 80)

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run End-to-End Video ANPR Test")
    parser.add_argument("--video", type=str, default=None, help="Path to input test video")
    parser.add_argument("--checkpoint", type=str, default="module3_incident_anpr/ocr_checkpoints/best_ocr_model.pt")
    parser.add_argument("--max-frames", type=int, default=None, help="Optional limit on frames to process")
    args = parser.parse_args()

    run_end_to_end_test(
        video_path=args.video,
        checkpoint_path=args.checkpoint,
        max_frames=args.max_frames
    )
