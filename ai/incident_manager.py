"""Incident Manager for Pothole Detection.

Groups consecutive detections of tracked potholes into persistent unique incidents.
Prevents duplicate incident creation across video frames.
Adapted from project_x/src/incident_manager.py into the ai subsystem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class TrackHistory:
    """Stores the observation history of an individual tracked object."""

    def __init__(self, track_id: int, initial_frame: int, initial_conf: float):
        self.track_id: int = track_id
        self.first_frame: int = initial_frame
        self.last_frame: int = initial_frame
        self.last_seen_frame: int = initial_frame
        self.consecutive_frames: int = 1
        self.detection_count: int = 1
        self.confidences: List[float] = [initial_conf]
        self.incident_id: Optional[int] = None

    def update(self, frame_idx: int, conf: float) -> None:
        if frame_idx == self.last_seen_frame + 1:
            self.consecutive_frames += 1
        else:
            self.consecutive_frames = 1

        self.last_seen_frame = frame_idx
        self.last_frame = frame_idx
        self.detection_count += 1
        self.confidences.append(conf)

    @property
    def max_confidence(self) -> float:
        return max(self.confidences) if self.confidences else 0.0


class IncidentManager:
    """Manages pothole incidents.

    A pothole track only becomes an incident when it is persistently detected
    for at least MIN_CONSECUTIVE_FRAMES.
    """

    def __init__(self, min_consecutive_frames: int = 3):
        self.min_consecutive_frames = min_consecutive_frames
        self.tracks: Dict[int, TrackHistory] = {}
        self.incidents: Dict[int, Dict[str, Any]] = {}  # keyed by incident_id
        self._track_to_incident: Dict[int, int] = {}    # maps track_id -> incident_id

    def update(self, frame_idx: int, active_detections: List[Dict[str, Any]], fps: float) -> None:
        """Update tracking history with detections from current frame.

        active_detections: list of dicts with:
            {
                "track_id": int,
                "confidence": float,
                "bbox": [x1, y1, x2, y2],
                "class_id": int,
                "class_name": str
            }
        """
        for det in active_detections:
            track_id = det.get("track_id")
            if track_id is None:
                continue

            conf = float(det.get("confidence", 0.0))

            if track_id not in self.tracks:
                self.tracks[track_id] = TrackHistory(track_id, frame_idx, conf)
            else:
                self.tracks[track_id].update(frame_idx, conf)

            track = self.tracks[track_id]

            # Check if this track qualifies to become a new incident
            if track.incident_id is None:
                if track.consecutive_frames >= self.min_consecutive_frames:
                    # Create new unique incident
                    new_incident_id = len(self.incidents) + 1
                    track.incident_id = new_incident_id
                    self._track_to_incident[track_id] = new_incident_id

                    # Timestamp based on the first frame it appeared
                    video_timestamp = round(track.first_frame / fps, 2) if fps > 0 else 0.0

                    self.incidents[new_incident_id] = {
                        "incident_id": new_incident_id,
                        "track_id": track_id,
                        "confidence": round(track.max_confidence, 2),
                        "first_frame": track.first_frame,
                        "last_frame": track.last_frame,
                        "video_timestamp": video_timestamp,
                        "detection_count": track.detection_count,
                    }
            else:
                # Update last frame for existing incident
                inc_id = track.incident_id
                if inc_id in self.incidents:
                    self.incidents[inc_id]["last_frame"] = track.last_frame
                    self.incidents[inc_id]["detection_count"] = track.detection_count
                    self.incidents[inc_id]["confidence"] = round(track.max_confidence, 2)

    def is_incident(self, track_id: Optional[int]) -> bool:
        """Return True if this track_id has been confirmed as an incident."""
        if track_id is None:
            return False
        return track_id in self._track_to_incident

    def get_incident_id(self, track_id: Optional[int]) -> Optional[int]:
        """Return the incident ID for a track_id, if confirmed."""
        if track_id is None:
            return None
        return self._track_to_incident.get(track_id)

    @property
    def total_incidents(self) -> int:
        """Return total count of confirmed unique incidents."""
        return len(self.incidents)

    def to_dict(self) -> Dict[str, Any]:
        """Export all incidents as a structured dictionary."""
        return {
            "total_incidents": self.total_incidents,
            "incidents": list(self.incidents.values()),
        }

    def save_json(self, output_path: str) -> None:
        """Save incident log to a JSON file."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)
        print(f"\n[INFO] Incident log successfully saved to: {out}")
        print(f"[INFO] Total Unique Incidents Recorded: {self.total_incidents}")
