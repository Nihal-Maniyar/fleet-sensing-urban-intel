"""Pothole Detection Module.

Performs frame-level and video-level detection using Ultralytics YOLO.
Adapted from project_x/src/detect_video.py into the ai subsystem.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np


def detect_frame(
    model: Any,
    frame: np.ndarray,
    conf_threshold: float = 0.35,
    device: str = "cpu",
) -> List[Dict[str, Any]]:
    """Run YOLO pothole detection on a single frame.

    Returns list of detections with:
        bbox: [x1, y1, x2, y2]
        confidence: float
        class_id: int
        class_name: str
        track_id: None
    """
    results = model.predict(
        source=frame,
        conf=conf_threshold,
        device=device,
        verbose=False,
    )

    detections = []
    if not results or len(results) == 0:
        return detections

    res = results[0]
    boxes = res.boxes
    if boxes is None:
        return detections

    names = model.names if hasattr(model, "names") else {}

    for box in boxes:
        xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
        conf = float(box.conf[0].cpu().numpy())
        cls_id = int(box.cls[0].cpu().numpy())
        raw_name = str(names.get(cls_id, "POTHOLE")).upper()
        cls_name = "POTHOLE" if "POTHOLE" in raw_name or "HOLE" in raw_name else "POTHOLE"

        detections.append({
            "bbox": xyxy,
            "confidence": conf,
            "class_id": cls_id,
            "class_name": cls_name,
            "track_id": None,
        })

    return detections
