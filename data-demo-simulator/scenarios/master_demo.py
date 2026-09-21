"""Scenario 5: Complete Master Demo flow.

Chains together the full end-to-end operational story:
1. Multi-bus pothole detection & corroboration on FC Road.
2. Network outage, SQLite WAL outbox buffering, and idempotent replay on Karve Road.
3. Diverse event sensing across Pune city corridors.
4. Post-repair observation supporting automated resolution verification.

Used for overall integration testing and as the rock-solid fallback during live demonstrations.
"""

from __future__ import annotations

from typing import List

try:
    from events.schema import Event
except (ImportError, ValueError):
    from ..events.schema import Event
from .base import BaseEmitter, BaseScenario
from .connectivity_outage import ConnectivityOutageScenario
from .diverse_events import DiverseEventsScenario
from .dual_bus_pothole import DualBusPotholeScenario
from .resolution_verification import ResolutionVerificationScenario


class MasterDemoScenario(BaseScenario):
    """Complete integrated scenario chaining all prototype capabilities."""

    name = "master_demo"
    description = (
        "Complete integrated demo sequence: dual-bus pothole corroboration, "
        "connectivity drop with SQLite WAL queue and replay, diverse event classes, "
        "and post-repair resolution verification."
    )

    def __init__(self, auto_generate_evidence: bool = True, db_path: str = "runtime/edge_outbox.db") -> None:
        self.auto_generate_evidence = auto_generate_evidence
        self.db_path = db_path
        self.scenario_pothole = DualBusPotholeScenario(base_sequence=1, auto_generate_evidence=auto_generate_evidence)
        self.scenario_outage = ConnectivityOutageScenario(
            base_sequence=10, auto_generate_evidence=auto_generate_evidence, db_path=db_path
        )
        self.scenario_diverse = DiverseEventsScenario(base_sequence=20, auto_generate_evidence=auto_generate_evidence)
        self.scenario_resolution = ResolutionVerificationScenario(
            base_sequence=30, auto_generate_evidence=auto_generate_evidence
        )

    def generate_events(self) -> List[Event]:
        """Generate full ordered list of all scenario events."""
        events: List[Event] = []
        events.extend(self.scenario_pothole.generate_events())
        events.extend(self.scenario_outage.generate_events())
        events.extend(self.scenario_diverse.generate_events())
        events.extend(self.scenario_resolution.generate_events())
        return events

    def run(self, emitter: BaseEmitter, delay_seconds: float = 0.0) -> List[Event]:
        """Run the master demo scenario end-to-end."""
        all_events: List[Event] = []

        # 1. Dual-bus pothole corroboration
        pothole_events = self.scenario_pothole.run(emitter=emitter, delay_seconds=delay_seconds)
        all_events.extend(pothole_events)

        # 2. Connectivity outage and WAL replay
        outage_events = self.scenario_outage.run(emitter=emitter, delay_seconds=delay_seconds)
        all_events.extend(outage_events)

        # 3. Diverse events
        diverse_events = self.scenario_diverse.run(emitter=emitter, delay_seconds=delay_seconds)
        all_events.extend(diverse_events)

        # 4. Resolution verification
        res_events = self.scenario_resolution.run(emitter=emitter, delay_seconds=delay_seconds)
        all_events.extend(res_events)

        return all_events
