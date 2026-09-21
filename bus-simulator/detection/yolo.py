"""YOLO object detector with pluggable weights and zero-binary computer-vision fallback.

Complies with AGENTS.md (no heavy model binaries in Git) and docs/ai-pipeline.md
(lightweight YOLO edge inference interface returning label, box, confidence, timestamp).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np

from .interface import ALLOWED_CLASSES, Detection

logger = logging.getLogger("actual_bus_simulator.detection")


class YOLODetector:
    """YOLO detector for road defect and civic event recognition."""

    def __init__(
        self,
        weights_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        target_classes: Optional[List[str]] = None,
    ) -> None:
        self.weights_path = weights_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.target_classes = target_classes or ALLOWED_CLASSES
        self.model = None
        self._injected_detections: List[Detection] = []

        if self.weights_path and Path(self.weights_path).exists():
            self._load_weights(self.weights_path)
        else:
            logger.info("Operating in zero-binary edge computer vision detector mode")

    def _load_weights(self, weights_path: str) -> None:
        """Attempt loading custom YOLO weights via Ultralytics."""
        try:
            from ultralytics import YOLO  # type: ignore

            self.model = YOLO(weights_path)
            logger.info("Loaded custom YOLO model from %s", weights_path)
        except Exception as e:
            logger.warning("Could not load weights '%s': %s. Falling back to edge detector.", weights_path, e)
            self.model = None

    def inject_detection(self, detection: Detection) -> None:
        """Inject a transient detection for deterministic testing or manual UI trigger."""
        self._injected_detections.append(detection)

    def detect(
        self,
        frame: np.ndarray,
        timestamp: Optional[str] = None,
    ) -> List[Detection]:
        """Run object detection on an image frame (H x W x C numpy array, BGR or RGB).

        Returns:
            List of Detection objects.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        detections: List[Detection] = []

        # 1. Check if model weights are loaded
        if self.model is not None:
            try:
                results = self.model(frame, conf=self.confidence_threshold, iou=self.iou_threshold, verbose=False)
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        cls_name = r.names.get(cls_id, "POTHOLE").upper()
                        # Map or normalize to allowed classes
                        if cls_name not in self.target_classes:
                            cls_name = "POTHOLE"
                        xyxy = box.xyxy[0].tolist()
                        detections.append(
                            Detection(
                                box=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                                confidence=conf,
                                class_name=cls_name,
                                class_id=cls_id,
                                timestamp=timestamp,
                            )
                        )
                return detections
            except Exception as e:
                logger.error("Error running YOLO model: %s", e)

        # 2. Built-in edge vision detector (runs out of the box with zero weight binaries)
        detections.extend(self._edge_vision_detect(frame, timestamp))

        # 3. Add any programmatically injected detections
        if self._injected_detections:
            detections.extend(self._injected_detections)
            self._injected_detections = []

        return detections

    def _edge_vision_detect(self, frame: np.ndarray, timestamp: str) -> List[Detection]:
        """Lightweight computer-vision road defect analysis.

        Detects dark depressive regions/potholes on the road plane (lower half of camera frame)
        using thresholding, contour geometry, and contrast ratios.
        """
        import cv2

        detections: List[Detection] = []
        h, w = frame.shape[:2]

        # In a bus dashboard camera, the road is situated in the lower portion of the frame
        road_y_start = int(h * 0.45)
        road_crop = frame[road_y_start:h, :]

        # Convert to grayscale
        if len(road_crop.shape) == 3:
            gray = cv2.cvtColor(road_crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = road_crop

        # Apply Gaussian blur to reduce asphalt grain noise
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # Calculate localized mean brightness of the asphalt
        mean_val = np.mean(blurred)

        # Potholes exhibit localized darker depressions or high-contrast texture
        # Using adaptive thresholding / dark spot detection
        _, dark_thresh = cv2.threshold(blurred, max(10, mean_val - 25), 255, cv2.THRESH_BINARY_INV)

        # Morphological opening to eliminate isolated pixel specks
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned = cv2.morphologyEx(dark_thresh, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Filter contours by realistic defect size on a 640x480 resolution frame
            min_area = (w * h) * 0.0015  # ~450 sq px on 640x480
            max_area = (w * h) * 0.15    # ~46,000 sq px

            if min_area <= area <= max_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                aspect_ratio = float(bw) / float(bh) if bh > 0 else 1.0

                # Road potholes are generally elliptical/horizontal perspective: aspect ratio ~ 0.5 to 3.5
                if 0.4 <= aspect_ratio <= 3.8:
                    # Confidence scored based on defect compactness and depth contrast
                    hull = cv2.convexHull(cnt)
                    hull_area = cv2.contourArea(hull)
                    solidity = float(area) / hull_area if hull_area > 0 else 0.5

                    # Defect mask mean
                    mask = np.zeros_like(gray)
                    cv2.drawContours(mask, [cnt], -1, 255, -1)
                    defect_mean = cv2.mean(gray, mask=mask)[0]
                    contrast = max(0.0, (mean_val - defect_mean) / (mean_val + 1e-5))

                    raw_conf = min(0.98, max(0.40, (solidity * 0.4) + (contrast * 0.6) + 0.3))

                    if raw_conf >= self.confidence_threshold:
                        global_y1 = float(road_y_start + y)
                        global_y2 = float(global_y1 + bh)
                        global_x1 = float(x)
                        global_x2 = float(x + bw)

                        detections.append(
                            Detection(
                                box=(global_x1, global_y1, global_x2, global_y2),
                                confidence=round(raw_conf, 2),
                                class_name="POTHOLE",
                                class_id=0,
                                timestamp=timestamp,
                            )
                        )

        return detections
