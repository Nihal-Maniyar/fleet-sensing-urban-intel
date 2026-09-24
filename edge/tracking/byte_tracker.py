"""ByteTrack multi-object tracking implementation.

Authentic two-stage detection association (high-confidence tier and low-confidence tier)
with Kalman filter bounding-box state estimation and consistent track ID continuity.
Complies with docs/ai-pipeline.md and docs/simulators.md.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from edge.detection.interface import Detection, compute_iou
except ImportError:
    try:
        from detection.interface import Detection, compute_iou
    except ImportError:
        from ..detection.interface import Detection, compute_iou


class TrackState(Enum):
    """Lifecycle state of a tracked object."""

    TENTATIVE = 1
    CONFIRMED = 2
    LOST = 3
    REMOVED = 4


class KalmanFilterBox:
    """Kalman filter for tracking bounding boxes in image space [x, y, a, h, vx, vy, va, vh].

    x, y: center point
    a: aspect ratio (width / height)
    h: height
    vx, vy, va, vh: respective velocities
    """

    def __init__(self) -> None:
        # State vector dimension: 8, measurement dimension: 4
        self.dim_x = 8
        self.dim_z = 4

        # State transition matrix F
        self.F = np.eye(self.dim_x, dtype=np.float32)
        for i in range(self.dim_z):
            self.F[i, i + self.dim_z] = 1.0  # position += velocity * dt

        # Measurement matrix H
        self.H = np.eye(self.dim_z, self.dim_x, dtype=np.float32)

        # Standard deviations
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

    def initiate(self, measurement: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
        """Create state mean and covariance from initial measurement [x, y, a, h]."""
        mean_pos = np.asarray(measurement, dtype=np.float32)
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]

        std = [
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std)).astype(np.float32)
        return mean, covariance

    def predict(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict next state using kinematic motion model."""
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel])).astype(np.float32)

        mean = np.dot(self.F, mean)
        covariance = np.linalg.multi_dot((self.F, covariance, self.F.T)) + motion_cov
        return mean, covariance

    def update(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        measurement: Sequence[float],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Correct predicted state with new bounding box measurement."""
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        measurement_cov = np.diag(np.square(std)).astype(np.float32)

        projected_mean = np.dot(self.H, mean)
        projected_cov = np.linalg.multi_dot((self.H, covariance, self.H.T)) + measurement_cov

        # Kalman gain K = P * H^T * (H * P * H^T + R)^(-1)
        kalman_gain = np.linalg.multi_dot((covariance, self.H.T, np.linalg.inv(projected_cov)))

        innovation = np.asarray(measurement, dtype=np.float32) - projected_mean
        new_mean = mean + np.dot(kalman_gain, innovation)
        new_covariance = covariance - np.linalg.multi_dot((kalman_gain, projected_cov, kalman_gain.T))
        return new_mean, new_covariance


class STrack:
    """Individual single-object track maintaining state, history, and Kalman filter."""

    _count: int = 0

    def __init__(
        self,
        box: Tuple[float, float, float, float],
        confidence: float,
        class_name: str,
    ) -> None:
        STrack._count += 1
        self.track_id: int = STrack._count

        self.box: Tuple[float, float, float, float] = box
        self.confidence: float = confidence
        self.class_name: str = class_name

        self.state: TrackState = TrackState.TENTATIVE
        self.is_activated: bool = False
        self.hits: int = 1
        self.age: int = 0
        self.time_since_update: int = 0

        self.kalman_filter = KalmanFilterBox()
        z = self._xyxy_to_xyah(self.box)
        self.mean, self.covariance = self.kalman_filter.initiate(z)

    @property
    def bbox(self) -> List[float]:
        return list(self.box)

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": [round(c, 2) for c in self.box],
            "state": self.state.name,
            "hits": self.hits,
        }

    @staticmethod
    def reset_counter() -> None:
        """Reset track counter (useful for clean scenario tests)."""
        STrack._count = 0

    @staticmethod
    def _xyxy_to_xyah(box: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        x1, y1, x2, y2 = box
        w = max(1.0, x2 - x1)
        h = max(1.0, y2 - y1)
        x = x1 + w / 2.0
        y = y1 + h / 2.0
        a = w / h
        return (x, y, a, h)

    @staticmethod
    def _xyah_to_xyxy(xyah: Sequence[float]) -> Tuple[float, float, float, float]:
        x, y, a, h = xyah[:4]
        w = a * h
        return (x - w / 2.0, y - h / 2.0, x + w / 2.0, y + h / 2.0)

    def predict(self) -> None:
        """Predict next bounding box position via Kalman filter."""
        self.mean, self.covariance = self.kalman_filter.predict(self.mean, self.covariance)
        self.box = self._xyah_to_xyxy(self.mean[:4])
        self.age += 1
        self.time_since_update += 1

    def update(self, detection: Detection) -> None:
        """Update track with matched detection."""
        z = self._xyxy_to_xyah(detection.box)
        self.mean, self.covariance = self.kalman_filter.update(self.mean, self.covariance, z)
        self.box = detection.box
        self.confidence = detection.confidence
        self.class_name = detection.class_name
        self.hits += 1
        self.time_since_update = 0

        if self.state == TrackState.TENTATIVE and self.hits >= 2:
            self.state = TrackState.CONFIRMED
            self.is_activated = True
        elif self.state == TrackState.LOST:
            self.state = TrackState.CONFIRMED

    def mark_lost(self) -> None:
        self.state = TrackState.LOST

    def mark_removed(self) -> None:
        self.state = TrackState.REMOVED


class ByteTracker:
    """ByteTrack algorithm coordinator.

    Matches detections to tracks in two stages:
      Stage 1: High-confidence detections matched against confirmed/active tracks.
      Stage 2: Remaining tracks matched against low-confidence detections.
    """

    def __init__(
        self,
        track_thresh: Optional[float] = None,
        low_thresh: float = 0.15,
        match_thresh: float = 0.70,  # Max IoU distance for matching (1 - IoU <= 0.7 => IoU >= 0.3)
        max_age: Optional[int] = None,
        min_hits: int = 2,
    ) -> None:
        import os
        if track_thresh is None:
            try:
                self.track_thresh = float(os.environ.get("TRACKER_CONFIDENCE_THRESHOLD", "0.45"))
            except ValueError:
                self.track_thresh = 0.45
        else:
            self.track_thresh = track_thresh

        if max_age is None:
            try:
                self.max_age = int(os.environ.get("TRACKER_MAX_AGE", "25"))
            except ValueError:
                self.max_age = 25
        else:
            self.max_age = max_age

        self.low_thresh = low_thresh
        self.match_thresh = match_thresh
        self.min_hits = min_hits

        self.tracked_tracks: List[STrack] = []  # Confirmed tracks
        self.lost_tracks: List[STrack] = []     # Lost tracks
        self.tentative_tracks: List[STrack] = []# Unconfirmed tracks
        self.frame_id: int = 0

    def update(self, detections: List[Detection]) -> List[STrack]:
        """Update tracker with frame detections.

        Returns:
            List of currently confirmed, active STrack objects.
        """
        self.frame_id += 1

        # Predict current locations for all existing tracks
        for t in self.tracked_tracks:
            t.predict()
        for t in self.lost_tracks:
            t.predict()
        for t in self.tentative_tracks:
            t.predict()

        # Split detections into high-confidence and low-confidence
        dets_high: List[Detection] = []
        dets_low: List[Detection] = []
        for det in detections:
            if det.confidence >= self.track_thresh:
                dets_high.append(det)
            elif det.confidence >= self.low_thresh:
                dets_low.append(det)

        # Candidate tracks for Stage 1: confirmed tracks + lost tracks
        active_candidates = [t for t in self.tracked_tracks if t.state == TrackState.CONFIRMED]
        lost_candidates = [t for t in self.lost_tracks if t.state == TrackState.LOST]
        pool_stage1 = active_candidates + lost_candidates

        # Stage 1: Associate high-confidence detections
        matched_tracks_1, unmatched_tracks_1, unmatched_dets_1 = self._associate(
            pool_stage1, dets_high, self.match_thresh
        )

        for track, det in matched_tracks_1:
            track.update(det)

        # Stage 2: Associate remaining tracks with low-confidence detections
        matched_tracks_2, unmatched_tracks_2, _ = self._associate(
            unmatched_tracks_1, dets_low, max_cost=0.85  # Slightly relaxed IoU threshold for low conf
        )

        for track, det in matched_tracks_2:
            track.update(det)

        # Handle remaining unmatched tracks
        for track in unmatched_tracks_2:
            if track.state == TrackState.CONFIRMED:
                track.mark_lost()
            elif track.state == TrackState.LOST and track.time_since_update > self.max_age:
                track.mark_removed()

        # Stage 3: Associate unmatched high-confidence detections with tentative tracks
        matched_tent, unmatched_tent, unmatched_high_final = self._associate(
            self.tentative_tracks, unmatched_dets_1, self.match_thresh
        )

        for track, det in matched_tent:
            track.update(det)

        for track in unmatched_tent:
            if track.time_since_update > 2:
                track.mark_removed()

        # Initialize new tentative tracks from remaining high-confidence detections
        for det in unmatched_high_final:
            new_track = STrack(det.box, det.confidence, det.class_name)
            if self.min_hits <= 1:
                new_track.state = TrackState.CONFIRMED
                new_track.is_activated = True
                self.tracked_tracks.append(new_track)
            else:
                self.tentative_tracks.append(new_track)

        # Re-organize track lists based on updated states
        all_tracks = self.tracked_tracks + self.lost_tracks + self.tentative_tracks

        self.tracked_tracks = [
            t for t in all_tracks
            if t.state == TrackState.CONFIRMED and t.time_since_update == 0
        ]
        self.lost_tracks = [
            t for t in all_tracks
            if t.state == TrackState.LOST and t.time_since_update <= self.max_age
        ]
        self.tentative_tracks = [
            t for t in all_tracks
            if t.state == TrackState.TENTATIVE
        ]

        # Return confirmed active tracks
        return self.tracked_tracks

    def _associate(
        self,
        tracks: List[STrack],
        detections: List[Detection],
        max_cost: float,
    ) -> Tuple[List[Tuple[STrack, Detection]], List[STrack], List[Detection]]:
        """Compute cost matrix based on IoU distance (1 - IoU) and perform greedy association."""
        if not tracks or not detections:
            return [], tracks.copy(), detections.copy()

        # Compute IoU matrix
        iou_matrix = np.zeros((len(tracks), len(detections)), dtype=np.float32)
        for i, trk in enumerate(tracks):
            for j, det in enumerate(detections):
                iou_matrix[i, j] = compute_iou(trk.box, det.box)

        # Cost = 1.0 - IoU
        cost_matrix = 1.0 - iou_matrix

        matched_tracks: List[Tuple[STrack, Detection]] = []
        matched_track_indices = set()
        matched_det_indices = set()

        # Greedy matching sorted by lowest cost (highest IoU)
        flat_indices = np.argsort(cost_matrix.ravel())
        for idx in flat_indices:
            r = idx // len(detections)
            c = idx % len(detections)

            if r in matched_track_indices or c in matched_det_indices:
                continue

            if cost_matrix[r, c] <= max_cost:
                matched_tracks.append((tracks[r], detections[c]))
                matched_track_indices.add(r)
                matched_det_indices.add(c)

        unmatched_tracks = [tracks[i] for i in range(len(tracks)) if i not in matched_track_indices]
        unmatched_detections = [detections[j] for j in range(len(detections)) if j not in matched_det_indices]

        return matched_tracks, unmatched_tracks, unmatched_detections
