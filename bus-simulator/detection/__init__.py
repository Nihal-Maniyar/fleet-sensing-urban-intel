"""Detection module interface and data models."""

from .interface import Detection, ALLOWED_CLASSES, compute_iou

__all__ = ["Detection", "ALLOWED_CLASSES", "compute_iou"]
