"""Scenario 3: Diverse urban sensing event classes.

Generates contract-valid events representing all 4 approved prototype event classes:
- POTHOLE
- GARBAGE
- TRAFFIC_OBSTRUCTION
- PEDESTRIAN_RISK

Used to verify backend department routing, severity derivation, and GIS layer filtering.
"""

from __future__ import annotations

from typing import List

try:
    from events.generator import EventGenerator
    from events.schema import Event
    from gps.simulator import GPSSimulator
    from routes.pune_routes import (
        FC_ROAD_ROUTE,
        JM_ROAD_ROUTE,
        KARVE_ROAD_ROUTE,
        SHIVAJI_ROAD_ROUTE,
    )
except (ImportError, ValueError):
    from ..events.generator import EventGenerator
    from ..events.schema import Event
    from ..gps.simulator import GPSSimulator
    from ..routes.pune_routes import (
        FC_ROAD_ROUTE,
        JM_ROAD_ROUTE,
        KARVE_ROAD_ROUTE,
        SHIVAJI_ROAD_ROUTE,
    )
from .base import BaseScenario


class DiverseEventsScenario(BaseScenario):
    """Scenario generating multiple distinct event types across Pune corridors."""

    name = "diverse_events"
    description = (
        "Generates all four candidate event types (POTHOLE, GARBAGE, "
        "TRAFFIC_OBSTRUCTION, PEDESTRIAN_RISK) across different Pune corridors."
    )

    def __init__(self, base_sequence: int = 10, auto_generate_evidence: bool = True) -> None:
        self.base_sequence = base_sequence
        self.auto_generate_evidence = auto_generate_evidence

    def generate_events(self) -> List[Event]:
        gen = EventGenerator(
            gps_simulator=GPSSimulator(seed=103),
            base_sequence=self.base_sequence,
            auto_generate_evidence_file=self.auto_generate_evidence,
        )

        events: List[Event] = []

        # 1. POTHOLE on FC Road near Dnyaneshwar Paduka Chowk
        events.append(
            gen.create_event(
                bus_id="BUS-001",
                event_type="POTHOLE",
                road_latitude=18.527800,
                road_longitude=73.842400,
                timestamp="2026-09-20T11:00:00Z",
                confidence=0.94,
                severity="HIGH",
                route_id=FC_ROAD_ROUTE.route_id,
                heading_degrees=15.0,
                deterministic_offset_meters=(1.1, -1.0),
                custom_event_id=f"EVT-{self.base_sequence:06d}",
            )
        )

        # 2. GARBAGE overflow near Swargate Station on Shivaji Road
        events.append(
            gen.create_event(
                bus_id="BUS-002",
                event_type="GARBAGE",
                road_latitude=18.501800,
                road_longitude=73.858000,
                timestamp="2026-09-20T11:15:00Z",
                confidence=0.87,
                severity="MEDIUM",
                route_id=SHIVAJI_ROAD_ROUTE.route_id,
                heading_degrees=350.0,
                deterministic_offset_meters=(-1.4, 0.9),
                custom_event_id=f"EVT-{(self.base_sequence + 1):06d}",
            )
        )

        # 3. TRAFFIC_OBSTRUCTION near Deccan Gymkhana junction
        events.append(
            gen.create_event(
                bus_id="BUS-003",
                event_type="TRAFFIC_OBSTRUCTION",
                road_latitude=18.515800,
                road_longitude=73.841800,
                timestamp="2026-09-20T11:30:00Z",
                confidence=0.91,
                severity="HIGH",
                route_id=KARVE_ROAD_ROUTE.route_id,
                heading_degrees=230.0,
                deterministic_offset_meters=(0.5, -1.8),
                custom_event_id=f"EVT-{(self.base_sequence + 2):06d}",
            )
        )

        # 4. PEDESTRIAN_RISK near Sambhaji Park crossing on JM Road
        events.append(
            gen.create_event(
                bus_id="BUS-001",
                event_type="PEDESTRIAN_RISK",
                road_latitude=18.525500,
                road_longitude=73.850000,
                timestamp="2026-09-20T11:45:00Z",
                confidence=0.82,
                severity="MEDIUM",
                route_id=JM_ROAD_ROUTE.route_id,
                heading_degrees=10.5,
                deterministic_offset_meters=(-0.7, 1.2),
                custom_event_id=f"EVT-{(self.base_sequence + 3):06d}",
            )
        )

        return events
