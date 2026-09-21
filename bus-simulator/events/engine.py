"""Temporal event decision engine with multi-frame persistence and suppression.

Guarantees that individual video frames do not become separate events.
Uses ByteTrack track continuity to establish persistence, extracts peak confidence
evidence frames, applies spatial suppression, and generates canonical EVT-XXXXXX events.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

try:
    from detection.interface import Detection
    from evidence.capture import capture_evidence_image
    from tracking.byte_tracker import STrack
    from events.schema import Event
except ImportError:
    from ..detection.interface import Detection
    from ..evidence.capture import capture_evidence_image
    from ..tracking.byte_tracker import STrack
    from .schema import Event

logger = logging.getLogger("actual_bus_simulator.events")


@dataclass
class TrackObservation:
    """Maintains observation state and best evidence frame for a single track ID."""

    track_id: int
    class_name: str
    first_seen_utc: str
    last_seen_utc: str
    hits: int = 1
    best_confidence: float = 0.0
    best_box: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    best_frame: Optional[np.ndarray] = None
    event_emitted: bool = False
    emitted_event_id: Optional[str] = None


class TemporalEventEngine:
    """Processes tracked objects across frames and generates contract-valid events."""

    def __init__(
        self,
        bus_id: str = "BUS-001",
        min_persistence_frames: int = 3,
        spatial_suppression_meters: float = 15.0,
        time_suppression_seconds: float = 30.0,
        start_event_seq: int = 1,
    ) -> None:
        self.bus_id = bus_id
        self.min_persistence_frames = min_persistence_frames
        self.spatial_suppression_meters = spatial_suppression_meters
        self.time_suppression_seconds = time_suppression_seconds
        self._event_seq: int = start_event_seq

        # Track ID -> TrackObservation
        self._observations: Dict[int, TrackObservation] = {}

        # History of emitted events for spatial-temporal suppression
        # (latitude, longitude, timestamp_epoch, event_type)
        self._recent_events: List[Tuple[float, float, float, str]] = []

    def _next_event_id(self) -> str:
        eid = f"EVT-{self._event_seq:06d}"
        self._event_seq += 1
        return eid

    def process_tracks(
        self,
        tracks: List[STrack],
        frame: np.ndarray,
        latitude: float,
        longitude: float,
        road_aligned_latitude: Optional[float] = None,
        road_aligned_longitude: Optional[float] = None,
        heading_degrees: Optional[float] = None,
        route_id: Optional[str] = None,
        connectivity_state: str = "ONLINE",
        timestamp: Optional[str] = None,
    ) -> List[Event]:
        """Update observations with active tracks from the current frame.

        Returns:
            List of new Event objects generated in this frame (if any).
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        new_events: List[Event] = []

        for track in tracks:
            tid = track.track_id
            if tid not in self._observations:
                self._observations[tid] = TrackObservation(
                    track_id=tid,
                    class_name=track.class_name,
                    first_seen_utc=timestamp,
                    last_seen_utc=timestamp,
                    hits=1,
                    best_confidence=track.confidence,
                    best_box=track.box,
                    best_frame=frame.copy(),
                )
            else:
                obs = self._observations[tid]
                obs.hits += 1
                obs.last_seen_utc = timestamp

                # Update best frame if current confidence is higher
                if track.confidence > obs.best_confidence:
                    obs.best_confidence = track.confidence
                    obs.best_box = track.box
                    obs.best_frame = frame.copy()

            obs = self._observations[tid]

            # Trigger event candidate when persistence criteria met and not already emitted
            if obs.hits >= self.min_persistence_frames and not obs.event_emitted:
                # Check spatial-temporal suppression
                eff_lat = road_aligned_latitude if road_aligned_latitude is not None else latitude
                eff_lon = road_aligned_longitude if road_aligned_longitude is not None else longitude

                if not self._is_suppressed(eff_lat, eff_lon, obs.class_name):
                    event_id = self._next_event_id()
                    obs.event_emitted = True
                    obs.emitted_event_id = event_id

                    # Derive severity
                    severity = self._derive_severity(obs.class_name, obs.best_confidence, obs.best_box)

                    # Save evidence image
                    evidence_rel_path = f"runtime/evidence/{event_id}.jpg"
                    if obs.best_frame is not None:
                        capture_evidence_image(
                            file_path=evidence_rel_path,
                            frame=obs.best_frame,
                            box=obs.best_box,
                            event_id=event_id,
                            bus_id=self.bus_id,
                            event_type=obs.class_name,
                            confidence=obs.best_confidence,
                            track_id=obs.track_id,
                            timestamp=timestamp,
                            latitude=eff_lat,
                            longitude=eff_lon,
                            severity=severity,
                        )

                    event = Event(
                        event_id=event_id,
                        bus_id=self.bus_id,
                        event_type=obs.class_name,
                        timestamp=timestamp,
                        latitude=round(latitude, 6),
                        longitude=round(longitude, 6),
                        road_aligned_latitude=round(road_aligned_latitude, 6) if road_aligned_latitude else None,
                        road_aligned_longitude=round(road_aligned_longitude, 6) if road_aligned_longitude else None,
                        heading_degrees=round(heading_degrees, 1) if heading_degrees is not None else None,
                        route_id=route_id,
                        confidence=round(obs.best_confidence, 2),
                        severity=severity,
                        evidence_image=evidence_rel_path,
                        source="actual_bus_simulator",
                        connectivity_state=connectivity_state,
                    )

                    new_events.append(event)
                    self._record_suppression(eff_lat, eff_lon, obs.class_name)
                    logger.info("Generated Event %s for Track #%d (%s, conf=%.2f)", event_id, tid, obs.class_name, obs.best_confidence)
                else:
                    # Mark emitted so we don't repeatedly check a suppressed track
                    obs.event_emitted = True
                    logger.debug("Suppressed duplicate event for Track #%d near (%.4f, %.4f)", tid, eff_lat, eff_lon)

        return new_events

    def _derive_severity(
        self,
        event_type: str,
        confidence: float,
        box: Tuple[float, float, float, float],
    ) -> str:
        """Derive prototype severity (LOW, MEDIUM, HIGH) from defect size & confidence."""
        x1, y1, x2, y2 = box
        area = max(0.0, x2 - x1) * max(0.0, y2 - y1)

        # Baseline severity derivation
        if event_type == "POTHOLE":
            if confidence >= 0.80 and area > 6000:
                return "HIGH"
            elif confidence >= 0.60 or area > 3000:
                return "MEDIUM"
            else:
                return "LOW"
        elif event_type == "TRAFFIC_OBSTRUCTION":
            return "HIGH" if area > 8000 else "MEDIUM"
        else:
            return "HIGH" if confidence >= 0.85 else "MEDIUM"

    def _is_suppressed(self, lat: float, lon: float, event_type: str) -> bool:
        """Check if an event of same type occurred within spatial & temporal suppression window."""
        now_epoch = datetime.now(timezone.utc).timestamp()
        # Clean older suppression entries
        self._recent_events = [
            e for e in self._recent_events if (now_epoch - e[2]) <= self.time_suppression_seconds
        ]

        for prev_lat, prev_lon, prev_time, prev_type in self._recent_events:
            if prev_type == event_type:
                dist = self._haversine_distance(lat, lon, prev_lat, prev_lon)
                if dist <= self.spatial_suppression_meters:
                    return True
        return False

    def _record_suppression(self, lat: float, lon: float, event_type: str) -> None:
        now_epoch = datetime.now(timezone.utc).timestamp()
        self._recent_events.append((lat, lon, now_epoch, event_type))

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return distance in meters between two WGS84 coordinates."""
        r = 6371000.0  # Earth radius in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        )
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
