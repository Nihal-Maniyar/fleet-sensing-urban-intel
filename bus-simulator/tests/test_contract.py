"""Tests for strict compliance with docs/api-contract.md."""

import unittest
from pathlib import Path
import sys

# Ensure bus-simulator directory is on path
sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from events.schema import Event


class TestAPIContract(unittest.TestCase):
    """Verify Event schema strictly matches docs/api-contract.md."""

    def test_valid_event_creation(self):
        event = Event(
            event_id="EVT-000001",
            bus_id="BUS-001",
            event_type="POTHOLE",
            timestamp="2026-09-20T10:30:00Z",
            latitude=18.5204,
            longitude=73.8567,
            road_aligned_latitude=18.5203,
            road_aligned_longitude=73.8568,
            heading_degrees=92.4,
            route_id="ROUTE-PUNE-FC",
            confidence=0.91,
            severity="HIGH",
            evidence_image="runtime/evidence/EVT-000001.jpg",
            source="actual_bus_simulator",
            connectivity_state="ONLINE",
        )
        self.assertEqual(event.event_id, "EVT-000001")
        self.assertEqual(event.bus_id, "BUS-001")
        self.assertEqual(event.source, "actual_bus_simulator")
        self.assertEqual(event.confidence, 0.91)

    def test_serialization_roundtrip(self):
        event = Event(
            event_id="EVT-000002",
            bus_id="BUS-002",
            event_type="GARBAGE",
            timestamp="2026-09-20T11:00:00Z",
            latitude=18.5255,
            longitude=73.8500,
            confidence=0.85,
            evidence_image="runtime/evidence/EVT-000002.jpg",
            source="actual_bus_simulator",
        )
        json_str = event.to_json()
        restored = Event.from_json(json_str)
        self.assertEqual(event.event_id, restored.event_id)
        self.assertEqual(event.bus_id, restored.bus_id)
        self.assertEqual(event.latitude, restored.latitude)
        self.assertEqual(event.confidence, restored.confidence)

    def test_invalid_event_id_raises(self):
        with self.assertRaises(ValueError):
            Event(
                event_id="INVALID-01",
                bus_id="BUS-001",
                event_type="POTHOLE",
                timestamp="2026-09-20T10:30:00Z",
                latitude=18.5204,
                longitude=73.8567,
                confidence=0.9,
                evidence_image="runtime/evidence/test.jpg",
                source="actual_bus_simulator",
            )

    def test_invalid_bus_id_raises(self):
        with self.assertRaises(ValueError):
            Event(
                event_id="EVT-000001",
                bus_id="BUS1",  # Needs 3+ digits
                event_type="POTHOLE",
                timestamp="2026-09-20T10:30:00Z",
                latitude=18.5204,
                longitude=73.8567,
                confidence=0.9,
                evidence_image="runtime/evidence/test.jpg",
                source="actual_bus_simulator",
            )

    def test_invalid_source_raises(self):
        with self.assertRaises(ValueError):
            Event(
                event_id="EVT-000001",
                bus_id="BUS-001",
                event_type="POTHOLE",
                timestamp="2026-09-20T10:30:00Z",
                latitude=18.5204,
                longitude=73.8567,
                confidence=0.9,
                evidence_image="runtime/evidence/test.jpg",
                source="unsupported_source",
            )

    def test_invalid_coordinates_raises(self):
        with self.assertRaises(ValueError):
            Event(
                event_id="EVT-000001",
                bus_id="BUS-001",
                event_type="POTHOLE",
                timestamp="2026-09-20T10:30:00Z",
                latitude=195.0,  # Out of range [-90, 90]
                longitude=73.8567,
                confidence=0.9,
                evidence_image="runtime/evidence/test.jpg",
                source="actual_bus_simulator",
            )


if __name__ == "__main__":
    unittest.main()
