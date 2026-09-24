"""Unit tests for IncidentManager.

Verifies that:
1. Single/double frame detections do NOT create an incident.
2. 3 consecutive frames create exactly 1 unique incident.
3. 20 consecutive frames of the same track ID produce 1 incident, NOT 20.
4. Multiple distinct track IDs create distinct incidents.
5. JSON export adheres strictly to the required schema.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ai.incident_manager import IncidentManager


class TestIncidentManager(unittest.TestCase):
    """Test suite for IncidentManager logic."""

    def test_consecutive_frames_requirement(self) -> None:
        mgr = IncidentManager(min_consecutive_frames=3)
        fps = 30.0

        # Frame 1: Detection of Track 1
        mgr.update(
            frame_idx=1,
            active_detections=[{"track_id": 1, "confidence": 0.85, "bbox": [10, 10, 50, 50]}],
            fps=fps,
        )
        self.assertEqual(mgr.total_incidents, 0, "1 frame detection should NOT trigger an incident")
        self.assertFalse(mgr.is_incident(1))

        # Frame 2: Detection of Track 1
        mgr.update(
            frame_idx=2,
            active_detections=[{"track_id": 1, "confidence": 0.87, "bbox": [12, 12, 52, 52]}],
            fps=fps,
        )
        self.assertEqual(mgr.total_incidents, 0, "2 frame detection should NOT trigger an incident")
        self.assertFalse(mgr.is_incident(1))

        # Frame 3: Detection of Track 1 -> SHOULD trigger Incident #1!
        mgr.update(
            frame_idx=3,
            active_detections=[{"track_id": 1, "confidence": 0.89, "bbox": [15, 15, 55, 55]}],
            fps=fps,
        )
        self.assertEqual(mgr.total_incidents, 1, "3 consecutive frames MUST trigger Incident #1")
        self.assertTrue(mgr.is_incident(1))

    def test_twenty_frames_produce_one_incident(self) -> None:
        mgr = IncidentManager(min_consecutive_frames=3)
        fps = 25.0

        # Simulate 20 consecutive frames for Track 1
        for f in range(100, 120):
            mgr.update(
                frame_idx=f,
                active_detections=[{"track_id": 1, "confidence": 0.87, "bbox": [100, 100, 150, 150]}],
                fps=fps,
            )

        # Must produce ONE incident, NOT 20 incidents!
        self.assertEqual(mgr.total_incidents, 1, f"Expected exactly 1 incident, got {mgr.total_incidents}")
        inc = mgr.incidents[1]
        self.assertEqual(inc["incident_id"], 1)
        self.assertEqual(inc["track_id"], 1)
        self.assertEqual(inc["first_frame"], 100)
        self.assertEqual(inc["last_frame"], 119)
        self.assertEqual(inc["detection_count"], 20)
        self.assertEqual(inc["video_timestamp"], 4.0)

    def test_json_schema(self) -> None:
        mgr = IncidentManager(min_consecutive_frames=3)
        fps = 30.0

        # Track 1 across 5 frames
        for f in range(10, 15):
            mgr.update(
                frame_idx=f,
                active_detections=[{"track_id": 1, "confidence": 0.90, "bbox": [10, 10, 30, 30]}],
                fps=fps,
            )

        # Track 2 across 4 frames
        for f in range(20, 24):
            mgr.update(
                frame_idx=f,
                active_detections=[{"track_id": 2, "confidence": 0.78, "bbox": [50, 50, 80, 80]}],
                fps=fps,
            )

        self.assertEqual(mgr.total_incidents, 2)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            mgr.save_json(tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertIn("total_incidents", data)
            self.assertEqual(data["total_incidents"], 2)
            self.assertIn("incidents", data)
            self.assertEqual(len(data["incidents"]), 2)

            inc1 = data["incidents"][0]
            self.assertEqual(inc1["incident_id"], 1)
            self.assertEqual(inc1["track_id"], 1)
            self.assertEqual(inc1["confidence"], 0.90)
            self.assertEqual(inc1["first_frame"], 10)
            self.assertEqual(inc1["last_frame"], 14)
            self.assertEqual(inc1["detection_count"], 5)

            inc2 = data["incidents"][1]
            self.assertEqual(inc2["incident_id"], 2)
            self.assertEqual(inc2["track_id"], 2)
            self.assertEqual(inc2["confidence"], 0.78)
            self.assertEqual(inc2["first_frame"], 20)
            self.assertEqual(inc2["last_frame"], 23)
            self.assertEqual(inc2["detection_count"], 4)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
