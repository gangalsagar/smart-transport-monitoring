#!/usr/bin/env python3
"""
Step 12 Integration Test Runner:
Executes the newly redesigned Module 3 Continuous Surveillance & Incident-Triggered ANPR Pipeline
on test video: module3_incident_anpr/test video/test_video.mp4 (or module3_incident_monitoring/anpr/test video/test_video.mp4)

Outputs a comprehensive, machine-readable JSON telemetry file.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

# Add workspace to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
from shared.config import Config
from shared.camera.frame_packet import FramePacket
from edge.storage.alert_queue import AlertQueue
from module3_incident_monitoring.adapter import Module3IncidentAdapter
from module3_incident_monitoring.plate.plate_recognizer import ProductionANPRRecognizer


def find_test_video() -> Path:
    candidates = [
        PROJECT_ROOT / "module3_incident_monitoring" / "anpr" / "test video" / "test_video.mp4",
        PROJECT_ROOT / "module3_incident_anpr" / "test video" / "test_video.mp4",
        PROJECT_ROOT / "module3_incident_anpr" / "test_videos" / "test_video.mp4",
        PROJECT_ROOT / "module2_traffic" / "data" / "videos" / "test_video.mp4",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("Could not locate test_video.mp4 in candidate paths.")


def run_pipeline_test(output_json_path: Path):
    video_path = find_test_video()
    print(f"[TEST] Using test video: {video_path}")
    
    config = Config()
    
    # Initialize real production recognizer
    plate_recognizer = ProductionANPRRecognizer(
        checkpoint_path=str(PROJECT_ROOT / "models" / "crnn" / "best.pt") if (PROJECT_ROOT / "models" / "crnn" / "best.pt").exists() else None,
    )
    
    adapter = Module3IncidentAdapter(
        config=config,
        plate_recognizer=plate_recognizer,
    )
    
    # Set up alert queue (in-memory or test SQLite DB)
    db_path = PROJECT_ROOT / "module3_incident_monitoring" / "results" / "test_alert_queue.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    db_path.parent.mkdir(parents=True, exist_ok=True)
    alert_queue = AlertQueue(database_path=str(db_path))
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video capture: {video_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[TEST] Total frames: {total_frames}, FPS: {fps:.2f}")
    
    frame_idx = 0
    t0 = time.time()
    
    all_events: List[Dict[str, Any]] = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_idx += 1
        video_time_sec = frame_idx / fps
        
        packet = FramePacket(
            frame=frame,
            frame_number=frame_idx,
            timestamp=None,
            video_time_seconds=video_time_sec,
        )
        
        alerts = adapter.process_frame(packet)
        for alert_obj in alerts:
            # Enqueue into alert queue
            alert_queue.enqueue(alert_obj)
            payload = alert_obj.payload
            ev_dict = {
                "alert_id": alert_obj.alert_id,
                "incident_type": alert_obj.payload.get("event_type", "incident"),
                "frame_number": alert_obj.payload.get("frame_number", frame_idx),
                "severity": alert_obj.severity,
                "vehicle_track_id": alert_obj.payload.get("vehicle_track_id"),
                "involved_vehicle_tracks": alert_obj.payload.get("involved_vehicle_tracks", []),
                "plate_number": alert_obj.payload.get("plate_number"),
                "plate_confidence": alert_obj.payload.get("plate_confidence", 0.0),
                "plate_status": alert_obj.payload.get("plate_status", "unavailable"),
                "evidence_path": alert_obj.evidence.image_path if alert_obj.evidence else None,
                "annotated_frame_path": alert_obj.payload.get("annotated_frame_path"),
                "vehicle_crop_path": alert_obj.payload.get("vehicle_crop_path"),
                "plate_crop_path": alert_obj.payload.get("plate_crop_path"),
            }
            all_events.append(ev_dict)
            print(f"  --> [CONFIRMED INCIDENT] Frame {frame_idx}: {ev_dict['incident_type']} | Track {ev_dict['vehicle_track_id']} | Plate: {ev_dict['plate_number']} ({ev_dict['plate_status']})")
            
        if frame_idx % 50 == 0:
            print(f"Processed {frame_idx}/{total_frames} frames...")
            
    cap.release()
    elapsed = time.time() - t0
    effective_fps = frame_idx / elapsed if elapsed > 0 else 0
    
    telemetry = adapter.get_telemetry()
    
    results = {
        "video_path": str(video_path),
        "frames_processed": frame_idx,
        "execution_time_seconds": round(elapsed, 3),
        "fps": round(effective_fps, 2),
        "unique_tracks": telemetry.get("unique_tracks_surveilled", 0),
        "incident_candidates": telemetry.get("suspicious_candidates_evaluated", 0),
        "confirmed_incidents": telemetry.get("confirmed_incidents_total", len(all_events)),
        "anpr_invocations": telemetry.get("anpr_invocations_event_triggered", 0),
        "ocr_passes": telemetry.get("ocr_passes_executed", 0),
        "incidents_with_recognized_plates": sum(1 for e in all_events if e["plate_status"] == "recognized"),
        "incidents_with_unavailable_plates": sum(1 for e in all_events if e["plate_status"] != "recognized"),
        "incident_results": all_events,
    }
    
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n" + "=" * 60)
    print("SURVEILLANCE & EVENT-TRIGGERED ANPR PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Frames processed:             {results['frames_processed']}")
    print(f"Execution time:               {results['execution_time_seconds']} s")
    print(f"Throughput:                   {results['fps']} FPS")
    print(f"Unique tracks surveilled:     {results['unique_tracks']}")
    print(f"Suspicious incident hits:     {results['incident_candidates']}")
    print(f"Confirmed incidents:          {results['confirmed_incidents']}")
    print(f"ANPR invocations (event-only):{results['anpr_invocations']}")
    print(f"OCR inference passes:         {results['ocr_passes']}")
    print(f"Recognized plates:            {results['incidents_with_recognized_plates']}")
    print(f"Unavailable/low conf plates:  {results['incidents_with_unavailable_plates']}")
    print(f"Results saved to:             {output_json_path}")
    print("=" * 60)
    return results


if __name__ == "__main__":
    out_file = PROJECT_ROOT / "module3_incident_monitoring" / "results" / "surveillance_pipeline_results.json"
    run_pipeline_test(out_file)
