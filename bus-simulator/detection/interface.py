"""Interface definition and data structures for object detection inference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# Approved prototype event classes from docs/api-contract.md
ALLOWED_CLASSES = [
    "POTHOLE",
    "GARBAGE",
    "TRAFFIC_OBSTRUCTION",
    "PEDESTRIAN_RISK",
]


@dataclass
class Detection:
    """Bounding box detection from YOLO or visual detector."""

    # Box coordinates [x1, y1, x2, y2]
    box: Tuple[float, float, float, float]
    confidence: float
    class_name: str
    class_id: int = 0
    timestamp: Optional[str] = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence {self.confidence} must be between 0.0 and 1.0")
        if self.class_name not in ALLOWED_CLASSES:
            raise ValueError(
                f"Unknown class '{self.class_name}'. Must be one of {ALLOWED_CLASSES}"
            )

    @property
    def x1(self) -> float:
        return self.box[0]

    @property
    def y1(self) -> float:
        return self.box[1]

    @property
    def x2(self) -> float:
        return self.box[2]

    @property
    def y2(self) -> float:
        return self.box[3]

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


def compute_iou(
    box_a: Sequence[float],
    box_b: Sequence[float],
) -> float:
    """Compute Intersection over Union (IoU) between two [x1, y1, x2, y2] boxes."""
    xa1, ya1, xa2, ya2 = box_a[:4]
    xb1, yb1, xb2, yb2 = box_b[:4]

    inter_x1 = max(xa1, xb1)
    inter_y1 = max(ya1, yb1)
    inter_x2 = min(xa2, xb2)
    inter_y2 = min(ya2, yb2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    intersection = inter_w * inter_h

    if intersection <= 0.0:
        return 0.0

    area_a = max(0.0, xa2 - xa1) * max(0.0, ya2 - ya1)
    area_b = max(0.0, xb2 - xb1) * max(0.0, yb2 - yb1)
    union = area_a + area_b - intersection

    return intersection / union if union > 0.0 else 0.0
