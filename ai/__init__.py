"""AI & Edge Computer Vision module for Fleet Sensing Urban Intel."""

from ai.config import (
    MODEL_PATH,
    MODEL_CONFIDENCE_THRESHOLD,
    EVENT_CONFIDENCE_THRESHOLD,
    EVIDENCE_STORAGE_PATH,
    TRACKER_TYPE,
    DEVICE,
)
from ai.pipeline import AIPipeline

__all__ = [
    "AIPipeline",
    "MODEL_PATH",
    "MODEL_CONFIDENCE_THRESHOLD",
    "EVENT_CONFIDENCE_THRESHOLD",
    "EVIDENCE_STORAGE_PATH",
    "TRACKER_TYPE",
    "DEVICE",
]
