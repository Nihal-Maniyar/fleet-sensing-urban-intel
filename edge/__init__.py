"""Edge computing module for camera capture, YOLO detection, ByteTrack, and event handling."""

from edge.camera.stream import VideoStreamSource, OpenCVFileStream, SyntheticRoadStream
from edge.detection.interface import ALLOWED_CLASSES, Detection, compute_iou
from edge.detection.yolo import YOLODetector, detect_compute_device
from edge.tracking.byte_tracker import ByteTracker, STrack, TrackState
from edge.events.schema import Event, ALLOWED_EVENT_TYPES
from edge.events.engine import TemporalEventEngine
from edge.evidence.capture import capture_evidence_image
from edge.storage.outbox import SQLiteOutbox

__all__ = [
    "VideoStreamSource",
    "OpenCVFileStream",
    "SyntheticRoadStream",
    "ALLOWED_CLASSES",
    "Detection",
    "compute_iou",
    "YOLODetector",
    "detect_compute_device",
    "ByteTracker",
    "STrack",
    "TrackState",
    "Event",
    "ALLOWED_EVENT_TYPES",
    "TemporalEventEngine",
    "capture_evidence_image",
    "SQLiteOutbox",
]
