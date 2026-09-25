"""Central configuration for AI & Edge Computer Vision Sensing Pipeline.

Complies with docs/ai-pipeline.md and docs/api-contract.md.
Centralizes environment variables and defaults without hard-coding machine-specific paths.
"""

from __future__ import annotations

import os
from pathlib import Path

# Base Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = str(REPO_ROOT / "models" / "best.pt")
DEFAULT_VIDEO_PATH = str(REPO_ROOT / "data" / "videos" / "road_video.mp4")
DEFAULT_EVIDENCE_PATH = "runtime/evidence"

# Model Configuration
MODEL_PATH = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)
MODEL_CONFIDENCE_THRESHOLD = float(os.environ.get("MODEL_CONFIDENCE_THRESHOLD", "0.35"))
MODEL_IOU_THRESHOLD = float(os.environ.get("MODEL_IOU_THRESHOLD", "0.45"))
DEVICE = os.environ.get("DEVICE", "auto")

# ByteTrack Tracking Configuration
TRACKER_TYPE = os.environ.get("TRACKER_TYPE", "bytetrack")
TRACKER_CONFIDENCE_THRESHOLD = float(os.environ.get("TRACKER_CONFIDENCE_THRESHOLD", "0.40"))
TRACKER_LOW_THRESHOLD = float(os.environ.get("TRACKER_LOW_THRESHOLD", "0.15"))
TRACKER_MATCH_THRESHOLD = float(os.environ.get("TRACKER_MATCH_THRESHOLD", "0.70"))
TRACKER_MAX_AGE = int(os.environ.get("TRACKER_MAX_AGE", "30"))
TRACKER_MIN_HITS = int(os.environ.get("TRACKER_MIN_HITS", "2"))

# Event Engine Configuration
EVENT_CONFIDENCE_THRESHOLD = float(os.environ.get("EVENT_CONFIDENCE_THRESHOLD", "0.35"))
MIN_CONSECUTIVE_FRAMES = int(os.environ.get("EVENT_MIN_FRAMES", "3"))
SPATIAL_SUPPRESSION_METERS = float(os.environ.get("SPATIAL_SUPPRESSION_METERS", "15.0"))
TIME_SUPPRESSION_SECONDS = float(os.environ.get("TIME_SUPPRESSION_SECONDS", "30.0"))
EVIDENCE_STORAGE_PATH = os.environ.get("EVIDENCE_STORAGE_PATH", DEFAULT_EVIDENCE_PATH)

# Colors & Visualization (BGR)
COLOR_POTHOLE = (0, 0, 240)       # Vivid Red/Amber
COLOR_OBSTRUCTION = (0, 165, 255)  # Orange
COLOR_GARBAGE = (80, 180, 110)     # Greenish
COLOR_DEFAULT = (0, 215, 255)     # Yellow
COLOR_TRACK_CONFIRMED = (75, 220, 100) # Green
