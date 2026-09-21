"""Tests for temporal event decision engine and suppression policy."""

import unittest
from pathlib import Path
import sys
import numpy as np

sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from events.engine import TemporalEventEngine
from tracking.byte_tracker import STrack, TrackState


class TestTemporalEventEngine(unittest.TestCase):
    """Verify temporal event rules, persistence, and deduplication."""

    def setUp(self):
        STrack.reset_counter()
        self.engine = TemporalEventEngine(
            bus_id="BUS-001",
            min_persistence_frames=3,
            spatial_suppression_meters=15.0,
            time_suppression_seconds=30.0,
            start_event_seq=1,
        )
        self.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_persistence_requirement(self):
        # Create a confirmed track
        track = STrack(box=(200.0, 250.0, 280.0, 310.0), confidence=0.88, class_name="POTHOLE")
        track.state = TrackState.CONFIRMED

        # Frame 1: Hit 1 -> No event yet
        events1 = self.engine.process_tracks(
            tracks=[track],
            frame=self.blank_frame,
            latitude=18.5204,
            longitude=73.8567,
            timestamp="2026-09-20T10:30:00Z",
        )
        self.assertEqual(len(events1), 0)

        # Frame 2: Hit 2 -> No event yet
        events2 = self.engine.process_tracks(
            tracks=[track],
            frame=self.blank_frame,
            latitude=18.52041,
            longitude=73.85671,
            timestamp="2026-09-20T10:30:01Z",
        )
        self.assertEqual(len(events2), 0)

        # Frame 3: Hit 3 -> Persistence threshold reached! Generates EVT-000001
        events3 = self.engine.process_tracks(
            tracks=[track],
            frame=self.blank_frame,
            latitude=18.52042,
            longitude=73.85672,
            timestamp="2026-09-20T10:30:02Z",
        )
        self.assertEqual(len(events3), 1)
        self.assertEqual(events3[0].event_id, "EVT-000001")
        self.assertEqual(events3[0].bus_id, "BUS-001")
        self.assertEqual(events3[0].event_type, "POTHOLE")

        # Frame 4: Hit 4 -> Event must NOT be emitted again for the same track!
        events4 = self.engine.process_tracks(
            tracks=[track],
            frame=self.blank_frame,
            latitude=18.52043,
            longitude=73.85673,
            timestamp="2026-09-20T10:30:03Z",
        )
        self.assertEqual(len(events4), 0, "Must suppress duplicate frames for the same track")


if __name__ == "__main__":
    unittest.main()
