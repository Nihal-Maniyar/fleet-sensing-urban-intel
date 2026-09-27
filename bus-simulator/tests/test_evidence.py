"""Tests for evidence snapshot generation and annotation."""

import os
import tempfile
import unittest
from pathlib import Path
import sys
import numpy as np

sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from evidence.capture import capture_evidence_image


class TestEvidenceCapture(unittest.TestCase):
    """Verify evidence image generation on disk with bounding box and HUD."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_capture_evidence_file_creation(self):
        file_path = os.path.join(self.temp_dir.name, "EVT-000001.jpg")
        frame = np.full((480, 640, 3), 50, dtype=np.uint8)

        saved_path = capture_evidence_image(
            file_path=file_path,
            frame=frame,
            box=(200.0, 220.0, 320.0, 310.0),
            event_id="EVT-000001",
            bus_id="BUS-001",
            event_type="POTHOLE",
            confidence=0.92,
            track_id=1,
            timestamp="2026-09-20T10:30:00Z",
            latitude=18.5204,
            longitude=73.8567,
            severity="HIGH",
        )

        self.assertTrue(os.path.exists(saved_path))
        self.assertGreater(os.path.getsize(saved_path), 1000)

        # Verify it can be read back with cv2
        import cv2
        img = cv2.imread(saved_path)
        self.assertIsNotNone(img)
        self.assertEqual(img.shape, (480, 640, 3))


if __name__ == "__main__":
    unittest.main()
