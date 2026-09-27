"""Deterministic event generator for simulated transit observation pipelines."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

try:
    from gps.simulator import GPSSimulator
except (ImportError, ValueError):
    from ..gps.simulator import GPSSimulator
from .evidence import ensure_evidence_image
from .schema import Event


class EventGenerator:
    """Produces contract-valid deterministic events without computer vision dependencies."""

    def __init__(
        self,
        gps_simulator: Optional[GPSSimulator] = None,
        base_sequence: int = 1,
        auto_generate_evidence_file: bool = True,
    ) -> None:
        self.gps_sim = gps_simulator or GPSSimulator(seed=42)
        self._sequence = base_sequence
        self.auto_generate_evidence_file = auto_generate_evidence_file

    def next_event_id(self) -> str:
        """Generate formatted EVT-000001 sequence identifier."""
        event_id = f"EVT-{self._sequence:06d}"
        self._sequence += 1
        return event_id

    def set_sequence(self, seq: int) -> None:
        """Set event identifier sequence counter."""
        self._sequence = seq

    def create_event(
        self,
        bus_id: str,
        event_type: str,
        road_latitude: float,
        road_longitude: float,
        timestamp: Optional[str] = None,
        confidence: float = 0.91,
        severity: Optional[str] = "HIGH",
        route_id: Optional[str] = None,
        heading_degrees: Optional[float] = None,
        connectivity_state: str = "ONLINE",
        deterministic_offset_meters: Optional[Tuple[float, float]] = None,
        custom_event_id: Optional[str] = None,
        evidence_image_path: Optional[str] = None,
        is_repaired: bool = False,
    ) -> Event:
        """Generate a complete, contract-valid Event.

        Simulates realistic GNSS sensor noise while preserving the true road-aligned
        coordinates in separate fields.
        """
        event_id = custom_event_id or self.next_event_id()
        raw_lat, raw_lon = self.gps_sim.apply_noise(
            road_lat=road_latitude,
            road_lon=road_longitude,
            deterministic_offset_meters=deterministic_offset_meters,
        )

        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if evidence_image_path is None:
            evidence_image_path = f"runtime/evidence/{event_id}.jpg"

        if self.auto_generate_evidence_file:
            ensure_evidence_image(
                file_path=evidence_image_path,
                event_id=event_id,
                event_type=event_type,
                confidence=confidence,
                timestamp=timestamp,
                is_repaired=is_repaired,
            )

        return Event(
            event_id=event_id,
            bus_id=bus_id,
            event_type=event_type,
            timestamp=timestamp,
            latitude=raw_lat,
            longitude=raw_lon,
            road_aligned_latitude=round(road_latitude, 6),
            road_aligned_longitude=round(road_longitude, 6),
            heading_degrees=heading_degrees,
            route_id=route_id,
            confidence=round(confidence, 2),
            severity=severity,
            evidence_image=evidence_image_path,
            source="data_demo_simulator",
            connectivity_state=connectivity_state,
        )
