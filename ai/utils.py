"""Utility functions for Pothole Detection & Tracking.

Includes device detection, video verification, model downloading/validation,
and visual overlay helpers.
Adapted from project_x/src/utils.py into the ai subsystem.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

try:
    import torch
except ImportError:
    torch = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from ai.config import (
    COLOR_POTHOLE,
    COLOR_TRACK_CONFIRMED,
    MODEL_PATH,
)

# Visual Overlay Constants
HUD_BG_COLOR = (24, 24, 28)       # Dark theme panel background (BGR)
HUD_BORDER_COLOR = (70, 70, 85)   # Border color
HUD_TEXT_COLOR = (240, 240, 240)  # Primary text color
ACCENT_COLOR = (0, 165, 255)      # Orange accent (BGR)
POTHOLE_COLOR = (0, 140, 255)     # Orange/Amber bounding box
SUCCESS_COLOR = (75, 220, 100)    # Green for tracked incident
MODEL_DOWNLOAD_URL = "https://huggingface.co/Samdutse/pothole-yolov8/resolve/main/best.pt"


def get_device(preference: Optional[str] = None) -> str:
    """Detect whether CUDA, Apple Silicon MPS, or CPU should be used."""
    if preference:
        pref = preference.lower()
        if pref in ["cpu", "cuda", "mps"]:
            if pref == "cuda" and (torch is None or not torch.cuda.is_available()):
                return "cpu"
            if pref == "mps" and (torch is None or not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available())):
                return "cpu"
            return pref

    if torch is not None:
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    return "cpu"


def verify_model_file(model_path: str = MODEL_PATH, auto_download: bool = True) -> str:
    """Verify model file exists. If missing, check candidate locations or attempt download."""
    path = Path(model_path).resolve()
    if path.exists() and path.stat().st_size > 1024 * 1024:
        return str(path)

    # Check common fallback locations
    candidates = [
        Path("models/best.pt").resolve(),
        Path(__file__).resolve().parent.parent / "models" / "best.pt",
        Path("best.pt").resolve(),
    ]
    for cand in candidates:
        if cand.exists() and cand.stat().st_size > 1024 * 1024:
            return str(cand)

    path.parent.mkdir(parents=True, exist_ok=True)

    if not auto_download:
        raise FileNotFoundError(
            f"\n[ERROR] Model file not found at: {path}\n"
            f"Please download 'best.pt' from: {MODEL_DOWNLOAD_URL}\n"
        )

    print(f"\nModel not found at {path}. Downloading from Hugging Face: {MODEL_DOWNLOAD_URL}...")

    def _progress(count: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            percent = int(count * block_size * 100 / total_size)
            mb = (count * block_size) / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\rDownloading: {percent}% ({mb:.1f}/{total_mb:.1f} MB)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(MODEL_DOWNLOAD_URL, str(path), reporthook=_progress)
        print("\nDownload complete!")
    except Exception as e:
        if path.exists():
            path.unlink(missing_ok=True)
        raise RuntimeError(
            f"\n[ERROR] Automatic model download failed: {e}\n"
            f"Please manually download 'best.pt' and place at: {path}\n"
        ) from e

    return str(path)


def load_and_validate_model(model_path: str = MODEL_PATH, device: str = "cpu") -> Tuple[Any, Dict[int, str]]:
    """Load YOLO model and inspect classes."""
    if YOLO is None:
        raise ImportError(
            "[ERROR] Ultralytics is not installed. Please install with: pip install ultralytics"
        )

    verified_path = verify_model_file(model_path)
    model = YOLO(verified_path)

    try:
        model.to(device)
    except Exception:
        pass

    names = model.names if hasattr(model, "names") else {}
    return model, names


def verify_video_file(video_path: str) -> Dict[str, Any]:
    """Verify video exists, can be opened by OpenCV, and extract properties."""
    path = Path(video_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"[ERROR] Input video not found at: {path}")

    valid_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(f"[ERROR] Unsupported video extension: {path.suffix}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise IOError(f"[ERROR] OpenCV cannot open video file: {path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    ret, test_frame = cap.read()
    cap.release()

    if not ret or test_frame is None:
        raise IOError(f"[ERROR] Video file {path} contains no readable frames.")

    if fps <= 0 or np.isnan(fps):
        fps = 25.0

    return {
        "path": str(path),
        "fps": float(fps),
        "width": width,
        "height": height,
        "total_frames": max(0, total_frames),
    }


def draw_detection(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    label: str,
    confidence: float,
    track_id: Optional[int] = None,
    is_incident: bool = False,
) -> None:
    """Draw bounding box and formatted multi-line label."""
    x1, y1, x2, y2 = bbox
    box_color = SUCCESS_COLOR if is_incident else POTHOLE_COLOR

    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 4)

    lines = [f"{label}"]
    if track_id is not None:
        lines.append(f"ID: {track_id}")
    lines.append(f"Confidence: {confidence:.2f}")

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    thickness = 2
    line_height = 28

    max_w = 0
    for line in lines:
        (w, h), _ = cv2.getTextSize(line, font, font_scale, thickness)
        if w > max_w:
            max_w = w

    total_h = len(lines) * line_height + 10
    bg_w = max_w + 20

    label_y = y1 - total_h if y1 - total_h > 5 else y1 + 5
    label_x = max(5, x1)

    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (label_x, label_y),
        (label_x + bg_w, label_y + total_h),
        (15, 15, 20),
        -1,
    )
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    cv2.rectangle(frame, (label_x, label_y), (label_x + bg_w, label_y + total_h), box_color, 2)

    for i, line in enumerate(lines):
        text_y = label_y + (i + 1) * line_height - 6
        cv2.putText(
            frame,
            line,
            (label_x + 10, text_y),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )


def draw_hud_panel(
    frame: np.ndarray,
    frame_idx: int,
    total_frames: int,
    fps: float,
    detected_count: int,
    active_tracks_count: int,
    unique_incidents_count: int,
) -> None:
    """Draw information panel overlay."""
    panel_x, panel_y = 20, 20
    panel_w, panel_h = 360, 220

    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        HUD_BG_COLOR,
        -1,
    )
    cv2.addWeighted(overlay, 0.88, frame, 0.12, 0, frame)

    cv2.rectangle(
        frame,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        HUD_BORDER_COLOR,
        2,
    )
    cv2.rectangle(
        frame,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + 40),
        ACCENT_COLOR,
        -1,
    )

    cv2.putText(
        frame,
        "POTHOLE DETECTION",
        (panel_x + 16, panel_y + 28),
        cv2.FONT_HERSHEY_DUPLEX,
        0.75,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    total_str = f"/{total_frames}" if total_frames > 0 else ""
    info_lines = [
        f"Frame: {frame_idx}{total_str}",
        f"FPS: {fps:.1f}",
        f"Detected: {detected_count}",
        f"Active Tracks: {active_tracks_count}",
        f"Unique Incidents: {unique_incidents_count}",
    ]

    start_y = panel_y + 70
    for i, line in enumerate(info_lines):
        line_y = start_y + (i * 28)
        color = SUCCESS_COLOR if "Unique Incidents" in line and unique_incidents_count > 0 else (255, 255, 255)
        cv2.putText(
            frame,
            line,
            (panel_x + 16, line_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            1,
            cv2.LINE_AA,
        )
