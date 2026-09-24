"""End-to-end AI/Computer Vision sensing pipeline.

Integrates:
    Input Video (OpenCV sequential frame reader)
        ↓
    YOLO Detection (Pothole defect detector)
        ↓
    ByteTrack Tracking (Two-stage association & Kalman filter)
        ↓
    Annotated Video Output (High-visibility boxes, Track IDs, Confidence)
        ↓
    Event Engine (Temporal persistence & deduplication)
        ↓
    Evidence Image (Annotated snapshot saved to disk)
        ↓
    GPS + Timestamp integration
        ↓
    Contract-valid Event generation

Complies with docs/ai-pipeline.md and docs/api-contract.md.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Ensure root repository directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai.config import (
    DEVICE,
    EVENT_CONFIDENCE_THRESHOLD,
    EVIDENCE_STORAGE_PATH,
    MIN_CONSECUTIVE_FRAMES,
    MODEL_CONFIDENCE_THRESHOLD,
    MODEL_IOU_THRESHOLD,
    MODEL_PATH,
    SPATIAL_SUPPRESSION_METERS,
    TIME_SUPPRESSION_SECONDS,
    TRACKER_CONFIDENCE_THRESHOLD,
    TRACKER_LOW_THRESHOLD,
    TRACKER_MAX_AGE,
    TRACKER_MIN_HITS,
)

from edge.camera.stream import OpenCVFileStream, VideoStreamSource
from edge.detection.interface import ALLOWED_CLASSES, Detection
from edge.detection.yolo import YOLODetector, detect_compute_device
from edge.events.engine import TemporalEventEngine
from edge.events.schema import Event
from edge.evidence.capture import capture_evidence_image
from edge.tracking.byte_tracker import ByteTracker, STrack

logger = logging.getLogger("ai.pipeline")


class AIPipeline:
    """Unified AI Sensing Pipeline coordinating detection, tracking, and event generation."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        event_confidence_threshold: Optional[float] = None,
        bus_id: str = "BUS-001",
        device: Optional[str] = None,
        min_persistence_frames: Optional[int] = None,
        spatial_suppression_meters: Optional[float] = None,
        time_suppression_seconds: Optional[float] = None,
        evidence_storage_path: Optional[str] = None,
        start_event_seq: int = 1,
    ) -> None:
        self.bus_id = bus_id
        self.device = detect_compute_device(device or DEVICE)
        self.model_path = model_path or MODEL_PATH
        self.confidence_threshold = (
            confidence_threshold if confidence_threshold is not None else MODEL_CONFIDENCE_THRESHOLD
        )
        self.event_confidence_threshold = (
            event_confidence_threshold if event_confidence_threshold is not None else EVENT_CONFIDENCE_THRESHOLD
        )
        self.evidence_storage_path = evidence_storage_path or EVIDENCE_STORAGE_PATH

        # 1. Initialize YOLO Detector
        self.detector = YOLODetector(
            weights_path=self.model_path,
            confidence_threshold=self.confidence_threshold,
            iou_threshold=MODEL_IOU_THRESHOLD,
            device=self.device,
        )

        # 2. Initialize ByteTrack Multi-Object Tracker
        self.tracker = ByteTracker(
            track_thresh=self.confidence_threshold or TRACKER_CONFIDENCE_THRESHOLD,
            low_thresh=TRACKER_LOW_THRESHOLD,
            max_age=TRACKER_MAX_AGE,
            min_hits=TRACKER_MIN_HITS,
        )

        # 3. Initialize Temporal Event Engine
        self.event_engine = TemporalEventEngine(
            bus_id=self.bus_id,
            min_persistence_frames=min_persistence_frames or MIN_CONSECUTIVE_FRAMES,
            min_confidence=self.event_confidence_threshold,
            spatial_suppression_meters=spatial_suppression_meters or SPATIAL_SUPPRESSION_METERS,
            time_suppression_seconds=time_suppression_seconds or TIME_SUPPRESSION_SECONDS,
            start_event_seq=start_event_seq,
            evidence_storage_path=self.evidence_storage_path,
        )

    def process_frame(
        self,
        frame: np.ndarray,
        latitude: float = 18.5204,
        longitude: float = 73.8567,
        road_aligned_latitude: Optional[float] = None,
        road_aligned_longitude: Optional[float] = None,
        heading_degrees: Optional[float] = None,
        route_id: Optional[str] = "ROUTE-PUNE-FC",
        timestamp: Optional[str] = None,
        connectivity_state: str = "ONLINE",
    ) -> Tuple[np.ndarray, List[Detection], List[STrack], List[Event]]:
        """Process a single frame through YOLO -> ByteTrack -> Event Engine -> Overlay.

        Returns:
            Tuple of (annotated_frame, detections, tracks, new_events)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. YOLO Detection
        detections = self.detector.detect(frame, timestamp=timestamp)

        # 2. ByteTrack Multi-Object Tracking
        tracks = self.tracker.update(detections)

        # 3. Event Engine (persistence, deduplication, evidence capture)
        new_events = self.event_engine.process_tracks(
            tracks=tracks,
            frame=frame,
            latitude=latitude,
            longitude=longitude,
            road_aligned_latitude=road_aligned_latitude,
            road_aligned_longitude=road_aligned_longitude,
            heading_degrees=heading_degrees,
            route_id=route_id,
            connectivity_state=connectivity_state,
            timestamp=timestamp,
        )

        # 4. Render high-visibility display annotations
        annotated_frame = self.render_annotated_frame(
            frame=frame,
            tracks=tracks,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
        )

        return annotated_frame, detections, tracks, new_events

    def render_annotated_frame(
        self,
        frame: np.ndarray,
        tracks: List[STrack],
        timestamp: Optional[str] = None,
        latitude: float = 18.5204,
        longitude: float = 73.8567,
    ) -> np.ndarray:
        """Render clear, high-contrast bounding boxes, track IDs, confidence, and HUD."""
        display = frame.copy()
        h, w = display.shape[:2]
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Draw each active tracked defect
        for trk in tracks:
            x1, y1, x2, y2 = [int(v) for v in trk.box]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)

            box_color = (0, 0, 240) if trk.class_name == "POTHOLE" else (0, 180, 240)
            cv2.rectangle(display, (x1, y1), (x2, y2), box_color, 2)

            # High-visibility tag: POTHOLE 0.91 | Track ID: 7
            tag = f"{trk.class_name} {trk.confidence:.2f} | Track ID: {trk.track_id}"
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(display, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, y1), box_color, -1)
            cv2.putText(
                display,
                tag,
                (x1 + 3, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        # 2. Top HUD Bar
        cv2.rectangle(display, (0, 0), (w, 30), (15, 15, 20), -1)
        hud_left = f"{self.bus_id} | {timestamp} | Tracks: {len(tracks)}"
        cv2.putText(display, hud_left, (12, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)

        gps_text = f"GPS: {latitude:.5f}, {longitude:.5f}"
        (gw, _), _ = cv2.getTextSize(gps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.putText(display, gps_text, (w - gw - 12, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 210, 240), 1, cv2.LINE_AA)

        return display

    def process_video(
        self,
        input_video: str,
        output_video: Optional[str] = None,
        max_frames: int = 0,
        latitude_start: float = 18.5204,
        longitude_start: float = 73.8567,
        on_event_callback: Optional[Callable[[Event], None]] = None,
    ) -> Dict[str, Any]:
        """Process an input road video sequentially from start to finish.

        Args:
            input_video: Path to input .mp4 video file
            output_video: Optional path to save annotated output video (.mp4)
            max_frames: Maximum frames to process (0 = whole video)
            latitude_start: Starting simulated latitude
            longitude_start: Starting simulated longitude
            on_event_callback: Optional callback invoked whenever an Event is emitted

        Returns:
            Summary dictionary of processing results.
        """
        in_path = Path(input_video).resolve()
        if not in_path.exists():
            raise FileNotFoundError(f"Input video not found: {in_path}")

        stream = OpenCVFileStream(str(in_path), loop=False)
        fps = stream.fps
        width = stream.width
        height = stream.height
        total_frames = stream.total_frames

        writer = None
        if output_video:
            out_path = Path(output_video).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

        start_time = time.time()
        frame_idx = 0
        all_events: List[Event] = []
        total_detections = 0

        logger.info(
            "Starting video processing: %s (%dx%d @ %.1f FPS, %d frames)",
            in_path.name,
            width,
            height,
            fps,
            total_frames,
        )

        try:
            while True:
                ret, frame = stream.read()
                if not ret or frame is None:
                    break

                frame_idx += 1

                # Incremental GPS progression along corridor
                current_lat = latitude_start + (frame_idx * 0.00002)
                current_lon = longitude_start + (frame_idx * 0.00001)

                annotated, dets, tracks, events = self.process_frame(
                    frame=frame,
                    latitude=current_lat,
                    longitude=current_lon,
                )

                total_detections += len(dets)

                for ev in events:
                    all_events.append(ev)
                    logger.info("Event emitted at frame %d: %s (confidence=%.2f)", frame_idx, ev.event_id, ev.confidence)
                    if on_event_callback:
                        on_event_callback(ev)

                if writer is not None:
                    writer.write(annotated)

                if frame_idx % 50 == 0 or frame_idx == total_frames:
                    logger.info(
                        "Processed %d/%d frames | Tracks: %d | Events: %d",
                        frame_idx,
                        total_frames,
                        len(tracks),
                        len(all_events),
                    )

                if max_frames > 0 and frame_idx >= max_frames:
                    logger.info("Reached requested max frames limit (%d)", max_frames)
                    break

        finally:
            stream.release()
            if writer is not None:
                writer.release()
                logger.info("Saved annotated video to: %s", output_video)

        processing_time = time.time() - start_time
        avg_fps = (frame_idx / processing_time) if processing_time > 0 else 0.0

        return {
            "input_video": str(in_path),
            "output_video": str(output_video) if output_video else None,
            "total_frames": frame_idx,
            "total_detections": total_detections,
            "unique_events": len(all_events),
            "events": [e.to_dict() for e in all_events],
            "processing_time": round(processing_time, 2),
            "average_fps": round(avg_fps, 1),
            "device": self.device.upper(),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI & Computer Vision Pothole Sensing Pipeline")
    parser.add_argument("--video", type=str, default="project_x/input/road_video.mp4", help="Input road video file")
    parser.add_argument("--output", type=str, default=None, help="Output annotated video file (.mp4)")
    parser.add_argument("--model", type=str, default=None, help="YOLO model weights path (.pt)")
    parser.add_argument("--confidence", type=float, default=None, help="Detection confidence threshold")
    parser.add_argument("--event-confidence", type=float, default=None, help="Event confidence threshold")
    parser.add_argument("--device", type=str, default="auto", choices=["cpu", "cuda", "mps", "auto"])
    parser.add_argument("--bus-id", type=str, default="BUS-001", help="Bus identity identifier")
    parser.add_argument("--frames", type=int, default=0, help="Max frames to process (0 = full video)")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s")
    args = parse_args()

    pipeline = AIPipeline(
        model_path=args.model,
        confidence_threshold=args.confidence,
        event_confidence_threshold=args.event_confidence,
        bus_id=args.bus_id,
        device=args.device,
    )

    summary = pipeline.process_video(
        input_video=args.video,
        output_video=args.output,
        max_frames=args.frames,
    )

    print("\n========================================")
    print("AI SENSING PIPELINE COMPLETE")
    print("========================================")
    print(f"Input:           {summary['input_video']}")
    if summary['output_video']:
        print(f"Output Video:    {summary['output_video']}")
    print(f"Frames:          {summary['total_frames']}")
    print(f"Total Dets:      {summary['total_detections']}")
    print(f"Unique Events:   {summary['unique_events']}")
    print(f"Time:            {summary['processing_time']}s ({summary['average_fps']} FPS)")
    print(f"Device:          {summary['device']}")
    print("========================================\n")


if __name__ == "__main__":
    main()
