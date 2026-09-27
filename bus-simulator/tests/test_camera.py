"""Tests for synthetic road video generator and camera capture."""

import unittest
from pathlib import Path
import sys
import numpy as np

sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from camera.stream import SyntheticRoadStream


class TestCameraStream(unittest.TestCase):
    """Verify camera frame generation and defect simulation."""

    def test_synthetic_stream_frame_properties(self):
        stream = SyntheticRoadStream(width=640, height=480, fps=20, auto_spawn_interval_sec=0)
        ret, frame = stream.read()
        self.assertTrue(ret)
        self.assertIsInstance(frame, np.ndarray)
        self.assertEqual(frame.shape, (480, 640, 3))
        self.assertEqual(frame.dtype, np.uint8)

    def test_defect_spawn_and_pass_callback(self):
        passed_defects = []

        def on_pass(cls_name):
            passed_defects.append(cls_name)

        stream = SyntheticRoadStream(
            width=640,
            height=480,
            fps=20,
            auto_spawn_interval_sec=0,
            on_defect_pass_callback=on_pass,
        )
        stream.trigger_defect(class_name="POTHOLE", lane_offset=0.0)

        # Advance frames until defect passes the camera
        for _ in range(50):
            stream.read()

        self.assertIn("POTHOLE", passed_defects)


if __name__ == "__main__":
    unittest.main()
