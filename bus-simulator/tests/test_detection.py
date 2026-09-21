"""Tests for YOLO detection interface and inference fallbacks."""

import unittest
from pathlib import Path
import sys
import numpy as np

sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from detection.interface import Detection, compute_iou
from detection.yolo import YOLODetector
from camera.stream import SyntheticRoadStream


class TestDetection(unittest.TestCase):
    """Verify detection data structures and edge CV detector."""

    def test_detection_dataclass(self):
        det = Detection(
            box=(100.0, 200.0, 180.0, 260.0),
            confidence=0.88,
            class_name="POTHOLE",
        )
        self.assertEqual(det.width, 80.0)
        self.assertEqual(det.height, 60.0)
        self.assertEqual(det.area, 4800.0)
        self.assertEqual(det.center, (140.0, 230.0))

    def test_compute_iou(self):
        box1 = (0.0, 0.0, 10.0, 10.0)
        box2 = (0.0, 0.0, 10.0, 10.0)
        self.assertAlmostEqual(compute_iou(box1, box2), 1.0)

        box3 = (10.0, 10.0, 20.0, 20.0)
        self.assertAlmostEqual(compute_iou(box1, box3), 0.0)

        box4 = (5.0, 0.0, 15.0, 10.0)
        # Intersection = 5 * 10 = 50, Union = 100 + 100 - 50 = 150 -> IoU = 1/3
        self.assertAlmostEqual(compute_iou(box1, box4), 50.0 / 150.0)

    def test_edge_detector_on_synthetic_pothole(self):
        stream = SyntheticRoadStream(width=640, height=480, fps=20, auto_spawn_interval_sec=0)
        detector = YOLODetector(confidence_threshold=0.3)

        # Trigger defect and advance until it is in the road detection zone
        stream.trigger_defect("POTHOLE", lane_offset=0.0)
        found_pothole = False

        for _ in range(35):
            ret, frame = stream.read()
            detections = detector.detect(frame)
            for d in detections:
                if d.class_name == "POTHOLE" and d.confidence >= 0.3:
                    found_pothole = True
                    break
            if found_pothole:
                break

        self.assertTrue(found_pothole, "Detector should detect synthetic pothole in road plane")


if __name__ == "__main__":
    unittest.main()
