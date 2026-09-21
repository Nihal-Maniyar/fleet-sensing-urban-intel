"""Scenario 2: Connectivity outage, edge SQLite/WAL buffering, and idempotent replay.

Demonstrates an edge bus entering a cellular dead zone / underpass, recording an event
while OFFLINE, storing it in SQLite WAL outbox, and replaying it with the exact same
event_id and metadata upon reconnection.
"""

from __future__ import annotations

from typing import List, Optional

try:
    from events.generator import EventGenerator
    from events.schema import Event
    from events.storage import SQLiteOutbox
    from gps.simulator import GPSSimulator
    from routes.pune_routes import KARVE_ROAD_ROUTE
except (ImportError, ValueError):
    from ..events.generator import EventGenerator
    from ..events.schema import Event
    from ..events.storage import SQLiteOutbox
    from ..gps.simulator import GPSSimulator
    from ..routes.pune_routes import KARVE_ROAD_ROUTE
from .base import BaseEmitter, BaseScenario


class ConnectivityOutageScenario(BaseScenario):
    """Scenario demonstrating offline SQLite WAL buffering and idempotent replay."""

    name = "connectivity_outage"
    description = (
        "BUS-003 detects an event while online, enters an offline underpass on Karve Road, "
        "buffers an event in SQLite WAL, and replays it idempotently upon reconnection."
    )

    def __init__(
        self,
        base_sequence: int = 3,
        auto_generate_evidence: bool = True,
        db_path: str = "runtime/edge_outbox.db",
    ) -> None:
        self.base_sequence = base_sequence
        self.auto_generate_evidence = auto_generate_evidence
        self.db_path = db_path
        self.outbox = SQLiteOutbox(db_path=self.db_path)

    def generate_events(self) -> List[Event]:
        """Generate the events involved in the outage scenario."""
        gen = EventGenerator(
            gps_simulator=GPSSimulator(seed=102),
            base_sequence=self.base_sequence,
            auto_generate_evidence_file=self.auto_generate_evidence,
        )

        # Event 1: Online detection on Karve Road near Lakdi Pul
        event_online = gen.create_event(
            bus_id="BUS-003",
            event_type="POTHOLE",
            road_latitude=18.513500,
            road_longitude=73.838500,
            timestamp="2026-09-20T10:10:00Z",
            confidence=0.88,
            severity="MEDIUM",
            route_id=KARVE_ROAD_ROUTE.route_id,
            heading_degrees=240.0,
            connectivity_state="ONLINE",
            deterministic_offset_meters=(1.2, 1.5),
            custom_event_id=f"EVT-{self.base_sequence:06d}",
        )

        # Event 2: Offline detection inside Nal Stop transit corridor
        event_offline = gen.create_event(
            bus_id="BUS-003",
            event_type="GARBAGE",
            road_latitude=18.508500,
            road_longitude=73.826800,
            timestamp="2026-09-20T10:13:30Z",
            confidence=0.85,
            severity="MEDIUM",
            route_id=KARVE_ROAD_ROUTE.route_id,
            heading_degrees=242.5,
            connectivity_state="OFFLINE",
            deterministic_offset_meters=(-1.0, -0.8),
            custom_event_id=f"EVT-{(self.base_sequence + 1):06d}",
        )

        return [event_online, event_offline]

    def run(self, emitter: BaseEmitter, delay_seconds: float = 0.0) -> List[Event]:
        """Execute full scenario including local outbox buffering and replay."""
        events = self.generate_events()
        event_online, event_offline = events[0], events[1]

        # 1. Emit online event directly to transport
        emitter.emit(event_online)

        # 2. Simulate connectivity drop: queue offline event into SQLite WAL outbox
        self.outbox.enqueue(event_offline)

        # 3. Simulate connectivity restoration: retrieve pending events from WAL queue
        pending_events = self.outbox.get_pending()

        # 4. Replay queued events through transport with unmodified event_id
        replayed_events: List[Event] = []
        for pending in pending_events:
            if pending.event_id == event_offline.event_id:
                emitter.emit(pending)
                self.outbox.mark_replayed(pending.event_id)
                replayed_events.append(pending)

        emitter.close()
        return [event_online, event_offline]
