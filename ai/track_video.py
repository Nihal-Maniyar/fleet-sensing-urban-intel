"""Pothole Video Tracking Pipeline.

Performs frame-by-frame tracking with ByteTrack and YOLO,
identifies persistent incidents, and saves annotated video + JSON log.
Adapted from project_x/src/track_video.py into the ai subsystem.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np

from ai.config import (
    MIN_CONSECUTIVE_FRAMES,
    MODEL_CONFIDENCE_THRESHOLD,
    MODEL_PATH,
    TRACKER_TYPE,
)
from ai.detect_video import detect_frame
from ai.incident_manager import IncidentManager
from ai.utils import (
    draw_detection,
    draw_hud_panel,
    load_and_validate_model,
    verify_video_file,
)

DEFAULT_INPUT_VIDEO = "data/videos/road_video.mp4"
DEFAULT_OUTPUT_VIDEO = "runtime/output/pothole_detection.mp4"
DEFAULT_INCIDENT_JSON = "runtime/output/incidents.json"


def process_video(
    input_video: str = DEFAULT_INPUT_VIDEO,
    output_video: str = DEFAULT_OUTPUT_VIDEO,
    incident_json: str = DEFAULT_INCIDENT_JSON,
    model_path: str = MODEL_PATH,
    confidence: float = 0.35,
    tracker: str = "bytetrack.yaml",
    min_consecutive_frames: int = MIN_CONSECUTIVE_FRAMES,
    device: str = "cpu",
    enable_tracking: bool = True,
    max_frames: Optional[int] = None,
) -> Dict[str, Any]:
    """Main processing pipeline:

    INPUT VIDEO -> YOLO POTHOLE DETECTION -> BYTE TRACK ->
    UNIQUE INCIDENTS -> ANNOTATED VIDEO + INCIDENT JSON
    """
    video_info = verify_video_file(input_video)
    fps = video_info["fps"]
    width = video_info["width"]
    height = video_info["height"]
    total_frames = video_info["total_frames"]
    if max_frames and max_frames < total_frames:
        total_frames = max_frames

    out_video_path = Path(output_video).resolve()
    out_video_path.parent.mkdir(parents=True, exist_ok=True)

    out_json_path = Path(incident_json).resolve()
    out_json_path.parent.mkdir(parents=True, exist_ok=True)

    model, class_names = load_and_validate_model(model_path, device=device)

    cap = cv2.VideoCapture(video_info["path"])
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_video_path), fourcc, fps, (width, height))

    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        writer = cv2.VideoWriter(str(out_video_path), fourcc, fps, (width, height))

    if not writer.isOpened():
        cap.release()
        raise IOError(f"[ERROR] Could not initialize video writer for path: {out_video_path}")

    incident_mgr = IncidentManager(min_consecutive_frames=min_consecutive_frames)

    frame_idx = 0
    start_time = time.time()
    last_progress_time = start_time
    last_progress_frame = 0

    print(f"\nProcessing {input_video} on device {device.upper()}...")

    from edge.detection import Detection
    from edge.tracking import ByteTracker

    tracker_inst = ByteTracker(track_thresh=confidence, low_thresh=0.15, max_age=30, min_hits=2)

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            if max_frames and frame_idx > max_frames:
                break

            detections = []
            active_track_ids = set()

            raw_dets = detect_frame(model, frame, conf_threshold=confidence, device=device)

            if enable_tracking:
                det_objs = [
                    Detection(
                        box=(float(d["bbox"][0]), float(d["bbox"][1]), float(d["bbox"][2]), float(d["bbox"][3])),
                        confidence=d["confidence"],
                        class_name=d["class_name"],
                    )
                    for d in raw_dets
                ]
                active_tracks = tracker_inst.update(det_objs)
                for trk in active_tracks:
                    active_track_ids.add(trk.track_id)
                    detections.append({
                        "bbox": [int(v) for v in trk.box],
                        "confidence": trk.confidence,
                        "class_id": 0,
                        "class_name": trk.class_name,
                        "track_id": trk.track_id,
                    })
            else:
                detections = raw_dets

            incident_mgr.update(frame_idx, detections, fps)

            for det in detections:
                t_id = det.get("track_id")
                is_inc = incident_mgr.is_incident(t_id)
                draw_detection(
                    frame=frame,
                    bbox=det["bbox"],
                    label="Pothole",
                    confidence=det["confidence"],
                    track_id=t_id,
                    is_incident=is_inc,
                )

            now = time.time()
            elapsed_interval = now - last_progress_time
            frames_interval = frame_idx - last_progress_frame
            current_fps = (frames_interval / elapsed_interval) if elapsed_interval > 0 else fps

            draw_hud_panel(
                frame=frame,
                frame_idx=frame_idx,
                total_frames=total_frames,
                fps=current_fps,
                detected_count=len(detections),
                active_tracks_count=len(active_track_ids),
                unique_incidents_count=incident_mgr.total_incidents,
            )

            writer.write(frame)

            if frame_idx % 50 == 0 or frame_idx == total_frames:
                total_str = f"/{total_frames}" if total_frames > 0 else ""
                print(f"Frame: {frame_idx}{total_str} | FPS: {current_fps:.1f} | Detections: {len(detections)} | Incidents: {incident_mgr.total_incidents}")
                last_progress_time = now
                last_progress_frame = frame_idx

    finally:
        cap.release()
        writer.release()

    total_processing_time = time.time() - start_time
    incident_mgr.save_json(str(out_json_path))

    return {
        "input_video": str(video_info["path"]),
        "output_video": str(out_video_path),
        "incident_json": str(out_json_path),
        "total_frames": frame_idx,
        "unique_incidents": incident_mgr.total_incidents,
        "processing_time": total_processing_time,
        "device": device.upper(),
    }
