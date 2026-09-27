#!/usr/bin/env python3
"""CLI Entrypoint for Pothole Video Detection & Tracking System.

Usage:
    python scripts/run_pothole_tracker.py
    python scripts/run_pothole_tracker.py --input data/videos/road_video.mp4
    python scripts/run_pothole_tracker.py --confidence 0.35 --device mps
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai.config import (
    MIN_CONSECUTIVE_FRAMES,
    MODEL_CONFIDENCE_THRESHOLD,
    MODEL_PATH,
)
from ai.track_video import process_video
from ai.utils import get_device, verify_model_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pothole Video Detection and Tracking Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/videos/road_video.mp4",
        help="Path to input road video file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="runtime/output/pothole_detection.mp4",
        help="Path to save annotated output video",
    )
    parser.add_argument(
        "--json",
        type=str,
        default="runtime/output/incidents.json",
        help="Path to save incident log in JSON format",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=MODEL_PATH,
        help="Path to pothole YOLO weights (best.pt)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=MODEL_CONFIDENCE_THRESHOLD,
        help="Detection confidence threshold (0.0 to 1.0)",
    )
    parser.add_argument(
        "--min-frames",
        type=int,
        default=MIN_CONSECUTIVE_FRAMES,
        help="Minimum consecutive frames required to register unique incident",
    )
    parser.add_argument(
        "--no-tracking",
        action="store_true",
        help="Disable ByteTrack and run frame-by-frame detection only",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cpu", "cuda", "mps", None],
        help="Target compute device",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Maximum frames to process (useful for quick validation)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = get_device(args.device)

    print("=" * 70)
    print("  POTHOLE VIDEO DETECTION & TRACKING PIPELINE")
    print("=" * 70)
    print(f"  Input Video:        {args.input}")
    print(f"  Output Video:       {args.output}")
    print(f"  Incident JSON:      {args.json}")
    print(f"  Model Path:         {args.model}")
    print(f"  Confidence Thresh:  {args.confidence}")
    print(f"  Min Frames:         {args.min_frames}")
    print(f"  Tracking Enabled:   {not args.no_tracking}")
    print(f"  Compute Device:     {device.upper()}")
    print("=" * 70)

    results = process_video(
        input_video=args.input,
        output_video=args.output,
        incident_json=args.json,
        model_path=args.model,
        confidence=args.confidence,
        min_consecutive_frames=args.min_frames,
        device=device,
        enable_tracking=not args.no_tracking,
        max_frames=args.max_frames,
    )

    print("\n" + "=" * 70)
    print("  PROCESSING COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"  Total Frames:       {results['total_frames']}")
    print(f"  Unique Incidents:   {results['unique_incidents']}")
    print(f"  Processing Time:    {results['processing_time']:.1f}s")
    print(f"  Annotated Video:    {results['output_video']}")
    print(f"  Incident Report:    {results['incident_json']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
