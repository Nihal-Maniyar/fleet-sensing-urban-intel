"""Scenario 1: Dual-bus pothole corroboration.

Two independent buses (BUS-001 and BUS-002) traverse Fergusson College Road (FC Road)
in Pune and independently observe the same severe pothole near Goodluck Chowk within
a 5-minute window.

Provides the foundational test input for Fleet Fusion spatial-temporal clustering
and subsequent civic ticket dispatch (POT-2026-XXXXXX).
"""

from __future__ import annotations

from typing import List

try:
    from events.generator import EventGenerator
    from events.schema import Event
    from gps.simulator import GPSSimulator
    from routes.pune_routes import FC_ROAD_ROUTE
except (ImportError, ValueError):
    from ..events.generator import EventGenerator
    from ..events.schema import Event
    from ..gps.simulator import GPSSimulator
    from ..routes.pune_routes import FC_ROAD_ROUTE
from .base import BaseScenario


class DualBusPotholeScenario(BaseScenario):
    """Scenario demonstrating multi-bus corroboration on the same road defect."""

    name = "dual_bus_pothole"
    description = (
        "Two independent buses (BUS-001, BUS-002) detect the same pothole near "
        "Goodluck Chowk on FC Road with realistic GPS noise and road-alignment."
    )

    def __init__(self, base_sequence: int = 1, auto_generate_evidence: bool = True) -> None:
        self.base_sequence = base_sequence
        self.auto_generate_evidence = auto_generate_evidence

    def generate_events(self) -> List[Event]:
        gen = EventGenerator(
            gps_simulator=GPSSimulator(seed=101),
            base_sequence=self.base_sequence,
            auto_generate_evidence_file=self.auto_generate_evidence,
        )

        # True road-aligned pothole position on FC Road near Goodluck Chowk
        pothole_lat = 18.519600
        pothole_lon = 73.843600
        heading = 120.4
        route_id = FC_ROAD_ROUTE.route_id

        # Observation 1: BUS-001 at 10:30:00 UTC
        event_1 = gen.create_event(
            bus_id="BUS-001",
            event_type="POTHOLE",
            road_latitude=pothole_lat,
            road_longitude=pothole_lon,
            timestamp="2026-09-20T10:30:00Z",
            confidence=0.92,
            severity="HIGH",
            route_id=route_id,
            heading_degrees=heading,
            connectivity_state="ONLINE",
            deterministic_offset_meters=(1.8, -1.4),  # ~2.3m raw sensor noise
            custom_event_id=f"EVT-{self.base_sequence:06d}",
        )

        # Observation 2: BUS-002 at 10:34:20 UTC (4m 20s later)
        event_2 = gen.create_event(
            bus_id="BUS-002",
            event_type="POTHOLE",
            road_latitude=pothole_lat,
            road_longitude=pothole_lon,
            timestamp="2026-09-20T10:34:20Z",
            confidence=0.89,
            severity="HIGH",
            route_id=route_id,
            heading_degrees=119.8,
            connectivity_state="ONLINE",
            deterministic_offset_meters=(-1.5, 2.1),  # ~2.6m raw sensor noise
            custom_event_id=f"EVT-{(self.base_sequence + 1):06d}",
        )

        return [event_1, event_2]
