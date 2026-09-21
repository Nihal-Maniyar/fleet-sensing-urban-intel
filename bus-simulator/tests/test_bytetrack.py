"""Tests for ByteTrack multi-object tracking and track ID continuity."""

import unittest
from pathlib import Path
import sys

sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from detection.interface import Detection
from tracking.byte_tracker import ByteTracker, STrack, TrackState


class TestByteTrack(unittest.TestCase):
    """Verify ByteTrack multi-object tracking logic."""

    def setUp(self):
        STrack.reset_counter()

    def test_single_track_continuity(self):
        tracker = ByteTracker(track_thresh=0.5, low_thresh=0.15, min_hits=2)

        # Frame 1: Initial detection (tentative)
        det1 = Detection(box=(100.0, 100.0, 150.0, 150.0), confidence=0.85, class_name="POTHOLE")
        tracks1 = tracker.update([det1])
        # After 1 hit with min_hits=2, track is tentative (not returned as confirmed yet)
        self.assertEqual(len(tracks1), 0)

        # Frame 2: Nearby detection in next frame
        det2 = Detection(box=(102.0, 103.0, 152.0, 153.0), confidence=0.88, class_name="POTHOLE")
        tracks2 = tracker.update([det2])
        self.assertEqual(len(tracks2), 1)
        self.assertEqual(tracks2[0].track_id, 1)
        self.assertEqual(tracks2[0].class_name, "POTHOLE")

        # Frame 3: Track continuation with slight motion
        det3 = Detection(box=(105.0, 107.0, 155.0, 157.0), confidence=0.82, class_name="POTHOLE")
        tracks3 = tracker.update([det3])
        self.assertEqual(len(tracks3), 1)
        # Track ID must remain constant
        self.assertEqual(tracks3[0].track_id, 1)

    def test_two_stage_low_confidence_association(self):
        """ByteTrack must associate lower-confidence detection to existing active track."""
        tracker = ByteTracker(track_thresh=0.6, low_thresh=0.2, min_hits=1)

        # Frame 1: Strong detection confirms track
        det1 = Detection(box=(200.0, 200.0, 250.0, 250.0), confidence=0.85, class_name="POTHOLE")
        tracks1 = tracker.update([det1])
        self.assertEqual(len(tracks1), 1)
        tid = tracks1[0].track_id

        # Frame 2: Sudden confidence drop due to shadow/blur (e.g. 0.35 < track_thresh 0.6)
        det2 = Detection(box=(202.0, 203.0, 252.0, 253.0), confidence=0.35, class_name="POTHOLE")
        tracks2 = tracker.update([det2])

        # Track should be preserved via Stage 2 low-confidence matching
        self.assertEqual(len(tracks2), 1)
        self.assertEqual(tracks2[0].track_id, tid)


if __name__ == "__main__":
    unittest.main()
