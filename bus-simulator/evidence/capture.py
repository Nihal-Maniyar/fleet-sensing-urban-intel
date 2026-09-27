"""Saves annotated evidence frames to disk for central dashboard and civic ticket review.

Complies with docs/api-contract.md (evidence_image path) and docs/ai-pipeline.md.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence, Tuple

import cv2
import numpy as np

logger = logging.getLogger("actual_bus_simulator.evidence")


def capture_evidence_image(
    file_path: str,
    frame: np.ndarray,
    box: Sequence[float],
    event_id: str,
    bus_id: str,
    event_type: str,
    confidence: float,
    track_id: Optional[int] = None,
    timestamp: str = "",
    latitude: float = 0.0,
    longitude: float = 0.0,
    severity: str = "HIGH",
) -> str:
    """Save an annotated evidence snapshot with bounding box and HUD to file_path.

    Returns:
        The normalized file path string.
    """
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Also ensure path in project root runtime/evidence exists
    repo_root = Path(__file__).resolve().parent.parent.parent
    root_target = (repo_root / file_path).resolve()
    root_target.parent.mkdir(parents=True, exist_ok=True)

    # Work on a copy of the frame
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    x1, y1, x2, y2 = [int(v) for v in box[:4]]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)

    # Choose box outline color based on severity
    color = (0, 0, 230) if severity == "HIGH" else (0, 165, 255) if severity == "MEDIUM" else (0, 215, 255)

    # 1. Bounding box
    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

    # 2. Defect label banner
    track_str = f" | Track #{track_id}" if track_id is not None else ""
    label_text = f"[{event_type}] {confidence:.2f}{track_str}"
    (text_w, text_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    banner_y1 = max(0, y1 - text_h - 8)
    banner_y2 = y1
    cv2.rectangle(annotated, (x1, banner_y1), (x1 + text_w + 8, banner_y2), color, -1)
    cv2.putText(
        annotated,
        label_text,
        (x1 + 4, banner_y2 - 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )

    # 3. Top HUD Banner
    cv2.rectangle(annotated, (0, 0), (w, 32), (20, 20, 25), -1)
    hud_left = f"AI SENSING - {bus_id} | {event_id} | {timestamp}"
    cv2.putText(
        annotated,
        hud_left,
        (10, 21),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )

    hud_right = f"POS: {latitude:.5f}, {longitude:.5f} | SEV: {severity}"
    (rw, _), _ = cv2.getTextSize(hud_right, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
    cv2.putText(
        annotated,
        hud_right,
        (w - rw - 10, 21),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (0, 230, 100) if severity == "LOW" else color,
        1,
        cv2.LINE_AA,
    )

    # Save to disk as standard JPEG
    success = cv2.imwrite(str(target), annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if root_target != target.resolve():
        try:
            cv2.imwrite(str(root_target), annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
        except Exception:
            pass
    if not success:
        logger.error("Failed writing evidence frame to %s", target)

    return str(target)
