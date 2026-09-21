"""Tests verifying deterministic execution of all 5 simulator scenarios."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent.parent
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

from scenarios.base import BaseEmitter
from scenarios.connectivity_outage import ConnectivityOutageScenario
from scenarios.diverse_events import DiverseEventsScenario
from scenarios.dual_bus_pothole import DualBusPotholeScenario
from scenarios.master_demo import MasterDemoScenario
from scenarios.resolution_verification import ResolutionVerificationScenario


class CollectingEmitter(BaseEmitter):
    """Test emitter that gathers events in memory."""

    def __init__(self) -> None:
        self.emitted = []

    def emit(self, event) -> bool:
        self.emitted.append(event)
        return True


class TestSimulatorScenarios(unittest.TestCase):
    """Test deterministic scenarios for consistency, coordinates, and contracts."""

    def test_dual_bus_pothole_scenario(self) -> None:
        """Scenario 1 produces two independent bus observations of the same pothole."""
        scenario = DualBusPotholeScenario(auto_generate_evidence=False)
        events = scenario.generate_events()

        self.assertEqual(len(events), 2)
        evt1, evt2 = events[0], events[1]

        # Independent buses
        self.assertEqual(evt1.bus_id, "BUS-001")
        self.assertEqual(evt2.bus_id, "BUS-002")

        # Same event type
        self.assertEqual(evt1.event_type, "POTHOLE")
        self.assertEqual(evt2.event_type, "POTHOLE")

        # Identical road-aligned position
        self.assertEqual(evt1.road_aligned_latitude, evt2.road_aligned_latitude)
        self.assertEqual(evt1.road_aligned_longitude, evt2.road_aligned_longitude)

        # Raw GPS positions have realistic slight jitter (~2-5 meters)
        self.assertNotEqual((evt1.latitude, evt1.longitude), (evt2.latitude, evt2.longitude))

        # Close in time (under 5 minutes)
        self.assertEqual(evt1.timestamp, "2026-09-20T10:30:00Z")
        self.assertEqual(evt2.timestamp, "2026-09-20T10:34:20Z")

    def test_connectivity_outage_scenario(self) -> None:
        """Scenario 2 tests offline WAL buffering and idempotent replay."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "outage_test.db")
            scenario = ConnectivityOutageScenario(auto_generate_evidence=False, db_path=db_path)

            emitter = CollectingEmitter()
            events = scenario.run(emitter=emitter)

            self.assertEqual(len(events), 2)
            self.assertEqual(events[0].connectivity_state, "ONLINE")
            self.assertEqual(events[1].connectivity_state, "OFFLINE")

            # Emitter received both the initial online event and the replayed offline event
            self.assertEqual(len(emitter.emitted), 2)
            # Replayed event preserved exact ID
            self.assertEqual(emitter.emitted[1].event_id, events[1].event_id)
            self.assertEqual(emitter.emitted[1].timestamp, events[1].timestamp)

            # SQLite outbox shows status REPLAYED
            self.assertEqual(scenario.outbox.count_pending(), 0)
            self.assertEqual(scenario.outbox.count_total(), 1)

    def test_diverse_events_scenario(self) -> None:
        """Scenario 3 produces all 4 prototype event classes."""
        scenario = DiverseEventsScenario(auto_generate_evidence=False)
        events = scenario.generate_events()

        self.assertEqual(len(events), 4)
        event_types = {e.event_type for e in events}
        expected_types = {"POTHOLE", "GARBAGE", "TRAFFIC_OBSTRUCTION", "PEDESTRIAN_RISK"}
        self.assertEqual(event_types, expected_types)

        # Confirm all buses use valid format
        for e in events:
            self.assertTrue(e.bus_id.startswith("BUS-"))
            self.assertTrue(e.event_id.startswith("EVT-"))

    def test_resolution_verification_scenario(self) -> None:
        """Scenario 4 produces before (defect) and after (repair) observations."""
        scenario = ResolutionVerificationScenario(auto_generate_evidence=False)
        events = scenario.generate_events()

        self.assertEqual(len(events), 2)
        before_evt, after_evt = events[0], events[1]

        # Exact same road-aligned coordinate
        self.assertEqual(before_evt.road_aligned_latitude, after_evt.road_aligned_latitude)
        self.assertEqual(before_evt.road_aligned_longitude, after_evt.road_aligned_longitude)

        # Before is HIGH severity defect, After is LOW severity repaired
        self.assertEqual(before_evt.severity, "HIGH")
        self.assertEqual(after_evt.severity, "LOW")

        # After is recorded later in time
        self.assertLess(before_evt.timestamp, after_evt.timestamp)

    def test_master_demo_scenario(self) -> None:
        """Scenario 5 chains all scenarios into an end-to-end demo execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "master_test.db")
            scenario = MasterDemoScenario(auto_generate_evidence=False, db_path=db_path)

            emitter = CollectingEmitter()
            events = scenario.run(emitter=emitter)

            # 2 (dual bus) + 2 (outage) + 4 (diverse) + 2 (resolution) = 10 events
            self.assertEqual(len(events), 10)
            self.assertEqual(len(emitter.emitted), 10)

            # Check that every single emitted event validates against v1 contract
            for evt in events:
                evt.validate()


if __name__ == "__main__":
    unittest.main()
