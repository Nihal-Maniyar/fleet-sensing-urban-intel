"""Scenario 4: Post-repair resolution verification.

Demonstrates the civic resolution verification loop:
1. Initial severe defect detection on FC Road by BUS-001 (Before Repair evidence).
2. Authority civic ticket (POT-2026-XXXXXX) lifecycle progression.
3. Subsequent observation by BUS-002 48 hours later at the exact same road-aligned
   coordinate capturing repaired road evidence (After Repair proof).

Enables the GIS dashboard and backend fusion to present side-by-side evidence
and validate transition to RESOLVED status.
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


class ResolutionVerificationScenario(BaseScenario):
    """Scenario modeling before-and-after evidence capture for ticket resolution."""

    name = "resolution_verification"
    description = (
        "Simulates initial defect detection by BUS-001, followed 48 hours later by "
        "BUS-002 capturing post-repair smooth asphalt evidence at the identical location."
    )

    def __init__(self, base_sequence: int = 20, auto_generate_evidence: bool = True) -> None:
        self.base_sequence = base_sequence
        self.auto_generate_evidence = auto_generate_evidence

    def generate_events(self) -> List[Event]:
        gen = EventGenerator(
            gps_simulator=GPSSimulator(seed=104),
            base_sequence=self.base_sequence,
            auto_generate_evidence_file=self.auto_generate_evidence,
        )

        pothole_lat = 18.519600
        pothole_lon = 73.843600
        route_id = FC_ROAD_ROUTE.route_id
        heading = 120.4

        # 1. Before Repair: BUS-001 detects pothole on 2026-09-20
        event_before = gen.create_event(
            bus_id="BUS-001",
            event_type="POTHOLE",
            road_latitude=pothole_lat,
            road_longitude=pothole_lon,
            timestamp="2026-09-20T08:00:00Z",
            confidence=0.93,
            severity="HIGH",
            route_id=route_id,
            heading_degrees=heading,
            deterministic_offset_meters=(1.5, -1.2),
            custom_event_id=f"EVT-{self.base_sequence:06d}",
            is_repaired=False,
        )

        # 2. After Repair: BUS-002 passes exact same location on 2026-09-22 (48h later)
        # Note: Event is recorded at the same road coordinates, with is_repaired=True
        # for evidence image rendering.
        event_after = gen.create_event(
            bus_id="BUS-002",
            event_type="POTHOLE",
            road_latitude=pothole_lat,
            road_longitude=pothole_lon,
            timestamp="2026-09-22T14:30:00Z",
            confidence=0.96,
            severity="LOW",
            route_id=route_id,
            heading_degrees=heading,
            deterministic_offset_meters=(-1.1, 1.8),
            custom_event_id=f"EVT-{(self.base_sequence + 1):06d}",
            is_repaired=True,
        )

        return [event_before, event_after]
