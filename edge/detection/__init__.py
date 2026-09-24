"""Edge YOLO detection and interfaces."""

from edge.detection.interface import ALLOWED_CLASSES, Detection, compute_iou
from edge.detection.yolo import YOLODetector, detect_compute_device

__all__ = [
    "ALLOWED_CLASSES",
    "Detection",
    "compute_iou",
    "YOLODetector",
    "detect_compute_device",
]
