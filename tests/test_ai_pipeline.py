"""Comprehensive tests for Group 1 AI & Computer Vision sensing pipeline.

Tests:
1. Video source initialization & metadata
2. Detection result structure & dictionary conversion
3. ByteTrack tracking & track ID continuity
4. Temporal Event Engine persistence & suppression
5. Duplicate-event prevention on continuous tracks
6. Evidence image creation and disk persistence
7. API contract compliance of generated Event objects
8. Bus-agnostic multi-bus operation
9. AIPipeline frame and video processing
"""

import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from ai.config import (
    MODEL_PATH,
    MODEL_CONFIDENCE_THRESHOLD,
    EVENT_CONFIDENCE_THRESHOLD,
    EVIDENCE_STORAGE_PATH,
)
from ai.pipeline import AIPipeline
from edge.camera import OpenCVFileStream, SyntheticRoadStream, VideoStreamSource
from edge.detection import ALLOWED_CLASSES, Detection, YOLODetector, compute_iou
from edge.events import ALLOWED_EVENT_TYPES, Event, TemporalEventEngine
from edge.evidence import capture_evidence_image
from edge.tracking import ByteTracker, STrack, TrackState


class TestAIPipeline(unittest.TestCase):
    """Test suite for AI / Computer Vision pipeline."""

    def setUp(self) -> None:
        self.test_evidence_dir = Path("runtime/test_evidence")
        self.test_evidence_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.test_evidence_dir.exists():
            shutil.rmtree(self.test_evidence_dir, ignore_errors=True)

    def test_video_source_initialization_and_metadata(self) -> None:
        """Verify video source abstraction exposes frame index, fps, dimensions, and sequential reading."""
        stream = SyntheticRoadStream(width=640, height=480, fps=20)
        self.assertEqual(stream.width, 640)
        self.assertEqual(stream.height, 480)
        self.assertEqual(stream.fps, 20.0)
        self.assertEqual(stream.frame_index, 0)
        self.assertEqual(stream.video_timestamp, 0.0)

        ret, frame = stream.read()
        self.assertTrue(ret)
        self.assertEqual(frame.shape, (480, 640, 3))
        self.assertEqual(stream.frame_index, 1)
        self.assertAlmostEqual(stream.video_timestamp, 0.05, places=3)

    def test_opencv_file_stream_properties(self) -> None:
        """Verify OpenCVFileStream initializes and handles video metadata."""
        # Create a small temporary 10-frame synthetic mp4 file
        temp_video = self.test_evidence_dir / "temp_road.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(temp_video), fourcc, 20.0, (320, 240))
        for _ in range(10):
            writer.write(np.zeros((240, 320, 3), dtype=np.uint8))
        writer.release()

        stream = OpenCVFileStream(str(temp_video), loop=False)
        self.assertEqual(stream.width, 320)
        self.assertEqual(stream.height, 240)
        self.assertEqual(stream.fps, 20.0)
        self.assertEqual(stream.total_frames, 10)

        meta = stream.get_metadata()
        self.assertEqual(meta["width"], 320)
        self.assertEqual(meta["height"], 240)

        # Read frames sequentially
        frames_read = 0
        while True:
            ret, frame = stream.read()
            if not ret or frame is None:
                break
            frames_read += 1
            self.assertEqual(stream.frame_index, frames_read)

        self.assertEqual(frames_read, 10)
        stream.release()

    def test_detection_result_structure(self) -> None:
        """Verify Detection dataclass enforces contract and converts to structured dict."""
        det = Detection(
            box=(50.0, 100.0, 200.0, 250.0),
            confidence=0.91,
            class_name="POTHOLE",
            class_id=0,
            timestamp="2026-09-24T18:00:00Z",
        )
        self.assertEqual(det.class_name, "POTHOLE")
        self.assertAlmostEqual(det.confidence, 0.91)
        self.assertEqual(det.bbox, [50.0, 100.0, 200.0, 250.0])
        self.assertEqual(det.width, 150.0)
        self.assertEqual(det.height, 150.0)

        d = det.to_dict()
        self.assertEqual(d["class_name"], "POTHOLE")
        self.assertEqual(d["confidence"], 0.91)
        self.assertEqual(d["bbox"], [50.0, 100.0, 200.0, 250.0])

    def test_tracking_result_structure_and_continuity(self) -> None:
        """Verify ByteTracker assigns stable track IDs across consecutive detections."""
        tracker = ByteTracker(track_thresh=0.40, low_thresh=0.15, max_age=5, min_hits=2)
        STrack.reset_counter()

        # Frame 1: Detection creates tentative track
        det1 = [Detection(box=(100.0, 100.0, 150.0, 150.0), confidence=0.85, class_name="POTHOLE")]
        tracks1 = tracker.update(det1)
        # min_hits=2, so not yet confirmed active
        self.assertEqual(len(tracks1), 0)

        # Frame 2: Same detection confirms active track
        det2 = [Detection(box=(102.0, 101.0, 152.0, 151.0), confidence=0.88, class_name="POTHOLE")]
        tracks2 = tracker.update(det2)
        self.assertEqual(len(tracks2), 1)
        assigned_id = tracks2[0].track_id
        self.assertEqual(tracks2[0].class_name, "POTHOLE")

        # Frame 3: Track continuity with slight motion
        det3 = [Detection(box=(105.0, 103.0, 155.0, 153.0), confidence=0.82, class_name="POTHOLE")]
        tracks3 = tracker.update(det3)
        self.assertEqual(len(tracks3), 1)
        self.assertEqual(tracks3[0].track_id, assigned_id)

        # Verify STrack dictionary structure
        t_dict = tracks3[0].to_dict()
        self.assertEqual(t_dict["track_id"], assigned_id)
        self.assertEqual(t_dict["class_name"], "POTHOLE")
        self.assertIn("bbox", t_dict)

    def test_temporal_event_generation_and_persistence(self) -> None:
        """Verify TemporalEventEngine requires min_persistence_frames before emitting event."""
        engine = TemporalEventEngine(
            bus_id="BUS-001",
            min_persistence_frames=3,
            min_confidence=0.50,
            evidence_storage_path=str(self.test_evidence_dir),
            start_event_seq=1,
        )
        STrack.reset_counter()
        track = STrack(box=(100.0, 100.0, 200.0, 200.0), confidence=0.85, class_name="POTHOLE")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Frame 1: Hit 1 -> No event
        events1 = engine.process_tracks([track], dummy_frame, latitude=18.5204, longitude=73.8567)
        self.assertEqual(len(events1), 0)

        # Frame 2: Hit 2 -> No event
        events2 = engine.process_tracks([track], dummy_frame, latitude=18.5204, longitude=73.8567)
        self.assertEqual(len(events2), 0)

        # Frame 3: Hit 3 (min_persistence_frames reached) -> Event emitted!
        events3 = engine.process_tracks([track], dummy_frame, latitude=18.5204, longitude=73.8567)
        self.assertEqual(len(events3), 1)
        event = events3[0]
        self.assertEqual(event.event_id, "EVT-000001")
        self.assertEqual(event.bus_id, "BUS-001")
        self.assertEqual(event.event_type, "POTHOLE")
        self.assertAlmostEqual(event.confidence, 0.85)

    def test_duplicate_event_prevention_on_continuous_track(self) -> None:
        """Verify continuous detections of the same tracked object DO NOT emit duplicate events."""
        engine = TemporalEventEngine(
            bus_id="BUS-001",
            min_persistence_frames=2,
            min_confidence=0.40,
            evidence_storage_path=str(self.test_evidence_dir),
            start_event_seq=1,
        )
        STrack.reset_counter()
        track = STrack(box=(120.0, 120.0, 220.0, 220.0), confidence=0.90, class_name="POTHOLE")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Hit 1 & 2 -> Emits Event 1
        engine.process_tracks([track], dummy_frame, latitude=18.5204, longitude=73.8567)
        events = engine.process_tracks([track], dummy_frame, latitude=18.5204, longitude=73.8567)
        self.assertEqual(len(events), 1)
        first_event_id = events[0].event_id

        # Hit 3, 4, 5, 6 for the same track MUST NOT emit any new events
        for _ in range(4):
            subsequent_events = engine.process_tracks([track], dummy_frame, latitude=18.5204, longitude=73.8567)
            self.assertEqual(len(subsequent_events), 0)

    def test_evidence_image_creation(self) -> None:
        """Verify capture_evidence_image writes an annotated image file with bounding box and HUD."""
        evidence_file = str(self.test_evidence_dir / "EVT-000042.jpg")
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 100

        res_path = capture_evidence_image(
            file_path=evidence_file,
            frame=frame,
            box=[150.0, 200.0, 300.0, 350.0],
            event_id="EVT-000042",
            bus_id="BUS-001",
            event_type="POTHOLE",
            confidence=0.92,
            track_id=5,
            timestamp="2026-09-24T18:00:00Z",
            latitude=18.5204,
            longitude=73.8567,
            severity="HIGH",
        )
        self.assertTrue(Path(res_path).exists())
        self.assertGreater(Path(res_path).stat().st_size, 500)

        # Verify saved image can be decoded by OpenCV
        saved_img = cv2.imread(res_path)
        self.assertIsNotNone(saved_img)
        self.assertEqual(saved_img.shape, (480, 640, 3))

    def test_contract_compliance_of_generated_event(self) -> None:
        """Verify generated Event object contains all required v1 contract fields with valid types."""
        engine = TemporalEventEngine(
            bus_id="BUS-002",
            min_persistence_frames=1,
            min_confidence=0.50,
            evidence_storage_path=str(self.test_evidence_dir),
            start_event_seq=101,
        )
        STrack.reset_counter()
        track = STrack(box=(100.0, 100.0, 200.0, 200.0), confidence=0.88, class_name="POTHOLE")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        events = engine.process_tracks(
            tracks=[track],
            frame=dummy_frame,
            latitude=18.5204,
            longitude=73.8567,
            road_aligned_latitude=18.5203,
            road_aligned_longitude=73.8568,
            heading_degrees=90.0,
            route_id="ROUTE-PUNE-JM",
            timestamp="2026-09-24T18:00:00Z",
        )
        self.assertEqual(len(events), 1)
        ev = events[0]

        # Contract requirements
        self.assertTrue(ev.event_id.startswith("EVT-"))
        self.assertEqual(ev.bus_id, "BUS-002")
        self.assertEqual(ev.event_type, "POTHOLE")
        self.assertAlmostEqual(ev.latitude, 18.5204)
        self.assertAlmostEqual(ev.longitude, 73.8567)
        self.assertAlmostEqual(ev.confidence, 0.88)
        self.assertEqual(ev.source, "actual_bus_simulator")
        self.assertTrue(ev.evidence_image.endswith(".jpg"))
        self.assertEqual(ev.timestamp, "2026-09-24T18:00:00Z")

        # Serializes cleanly to dictionary and JSON
        d = ev.to_dict()
        self.assertIn("event_id", d)
        self.assertIn("bus_id", d)
        self.assertIn("evidence_image", d)
        j = ev.to_json()
        self.assertIsInstance(j, str)

    def test_bus_agnostic_multiple_instances(self) -> None:
        """Verify pipeline can instantiate multiple independent bus IDs simultaneously."""
        pipe1 = AIPipeline(bus_id="BUS-001")
        pipe2 = AIPipeline(bus_id="BUS-002")
        pipe3 = AIPipeline(bus_id="BUS-003")

        self.assertEqual(pipe1.bus_id, "BUS-001")
        self.assertEqual(pipe2.bus_id, "BUS-002")
        self.assertEqual(pipe3.bus_id, "BUS-003")

    def test_pipeline_process_frame(self) -> None:
        """Verify end-to-end process_frame through YOLO -> ByteTrack -> Event Engine."""
        pipeline = AIPipeline(
            bus_id="BUS-001",
            min_persistence_frames=1,
            confidence_threshold=0.30,
            evidence_storage_path=str(self.test_evidence_dir),
        )

        # Inject a detection directly into detector for deterministic test
        now = "2026-09-24T18:00:00Z"
        pipeline.detector.inject_detection(
            Detection(
                box=(100.0, 100.0, 200.0, 200.0),
                confidence=0.88,
                class_name="POTHOLE",
                timestamp=now,
            )
        )

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        annotated, dets, tracks, events = pipeline.process_frame(
            frame=dummy_frame,
            latitude=18.5204,
            longitude=73.8567,
            timestamp=now,
        )

        self.assertEqual(annotated.shape, (480, 640, 3))
        self.assertGreaterEqual(len(dets), 1)
        self.assertEqual(dets[0].class_name, "POTHOLE")


if __name__ == "__main__":
    unittest.main()
