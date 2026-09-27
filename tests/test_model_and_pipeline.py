"""Model verification and environment test script.

Validates:
1. Python environment and device detection (CUDA / MPS / CPU).
2. Model loading from models/best.pt.
3. Model classes.
4. Inference test on a test image array.
5. HUD and bounding box drawing functions.
"""

from __future__ import annotations

import unittest
import numpy as np

from ai.config import MODEL_PATH
from ai.utils import (
    draw_detection,
    draw_hud_panel,
    get_device,
    load_and_validate_model,
)


class TestModelAndPipeline(unittest.TestCase):
    """Test suite for model loading and visualization utilities."""

    def test_device_detection(self) -> None:
        device = get_device()
        self.assertIn(device, ["cuda", "mps", "cpu"])

    def test_model_loading_and_inference(self) -> None:
        device = get_device()
        model, classes = load_and_validate_model(MODEL_PATH, device=device)
        self.assertIsNotNone(model)
        self.assertTrue(len(classes) > 0)

        # Inference sanity check
        dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        results = model.predict(source=dummy_frame, conf=0.25, device=device, verbose=False)
        self.assertTrue(len(results) > 0)

    def test_hud_and_overlay_rendering(self) -> None:
        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        draw_detection(test_frame, (100, 100, 200, 200), "Pothole", 0.92, track_id=1, is_incident=True)
        draw_hud_panel(
            test_frame,
            frame_idx=100,
            total_frames=1000,
            fps=25.0,
            detected_count=1,
            active_tracks_count=1,
            unique_incidents_count=1,
        )
        self.assertEqual(test_frame.shape, (720, 1280, 3))


if __name__ == "__main__":
    unittest.main()
