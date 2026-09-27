"""Contract tests verifying 100% adherence to docs/api-contract.md."""

import json
import sys
import unittest
from pathlib import Path

# Ensure simulator directory is in path
SIM_DIR = Path(__file__).resolve().parent.parent
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

from events.schema import Event


class TestAPIContract(unittest.TestCase):
    """Verifies that all events strictly satisfy the v1 API contract."""

    def setUp(self) -> None:
        self.valid_payload = {
            "event_id": "EVT-000001",
            "bus_id": "BUS-001",
            "event_type": "POTHOLE",
            "timestamp": "2026-09-20T10:30:00Z",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "road_aligned_latitude": 18.5203,
            "road_aligned_longitude": 73.8568,
            "heading_degrees": 92.4,
            "route_id": "ROUTE-A",
            "confidence": 0.91,
            "severity": "HIGH",
            "evidence_image": "runtime/evidence/EVT-000001.jpg",
            "source": "data_demo_simulator",
            "connectivity_state": "ONLINE",
        }

    def test_valid_contract_example_parses(self) -> None:
        """The canonical JSON example from docs/api-contract.md must parse cleanly."""
        event = Event.from_dict(self.valid_payload)
        self.assertEqual(event.event_id, "EVT-000001")
        self.assertEqual(event.bus_id, "BUS-001")
        self.assertEqual(event.event_type, "POTHOLE")
        self.assertEqual(event.confidence, 0.91)
        self.assertEqual(event.source, "data_demo_simulator")
        self.assertEqual(event.severity, "HIGH")

    def test_json_roundtrip_preserves_contract_fields(self) -> None:
        """Serializing to JSON and deserializing must retain all field names and values."""
        event = Event.from_dict(self.valid_payload)
        json_str = event.to_json()
        roundtripped = Event.from_json(json_str)

        self.assertEqual(event.to_dict(), roundtripped.to_dict())
        # Contract fields must not be renamed
        raw_dict = json.loads(json_str)
        expected_keys = {
            "event_id",
            "bus_id",
            "event_type",
            "timestamp",
            "latitude",
            "longitude",
            "road_aligned_latitude",
            "road_aligned_longitude",
            "heading_degrees",
            "route_id",
            "confidence",
            "severity",
            "evidence_image",
            "source",
            "connectivity_state",
        }
        self.assertEqual(set(raw_dict.keys()), expected_keys)

    def test_invalid_event_id_format_rejected(self) -> None:
        """event_id must match EVT-XXXXXX."""
        payload = dict(self.valid_payload)
        payload["event_id"] = "evt_001"
        with self.assertRaises(ValueError) as ctx:
            Event.from_dict(payload)
        self.assertIn("Invalid event_id", str(ctx.exception))

    def test_invalid_bus_id_format_rejected(self) -> None:
        """bus_id must match BUS-XXX."""
        payload = dict(self.valid_payload)
        payload["bus_id"] = "bus-1"
        with self.assertRaises(ValueError) as ctx:
            Event.from_dict(payload)
        self.assertIn("Invalid bus_id", str(ctx.exception))

    def test_disallowed_event_type_rejected(self) -> None:
        """event_type must be one of the agreed prototype classes."""
        payload = dict(self.valid_payload)
        payload["event_type"] = "ALIEN_INVASION"
        with self.assertRaises(ValueError) as ctx:
            Event.from_dict(payload)
        self.assertIn("Invalid event_type", str(ctx.exception))

    def test_all_allowed_event_types_accepted(self) -> None:
        """POTHOLE, GARBAGE, TRAFFIC_OBSTRUCTION, and PEDESTRIAN_RISK are allowed."""
        for et in ("POTHOLE", "GARBAGE", "TRAFFIC_OBSTRUCTION", "PEDESTRIAN_RISK"):
            payload = dict(self.valid_payload)
            payload["event_type"] = et
            event = Event.from_dict(payload)
            self.assertEqual(event.event_type, et)

    def test_timestamp_utc_iso8601_enforced(self) -> None:
        """timestamp must be UTC ending in 'Z'."""
        payload = dict(self.valid_payload)
        payload["timestamp"] = "2026-09-20 10:30:00"  # Missing T and Z
        with self.assertRaises(ValueError) as ctx:
            Event.from_dict(payload)
        self.assertIn("Invalid timestamp", str(ctx.exception))

    def test_confidence_range_enforced(self) -> None:
        """confidence must be between 0.0 and 1.0."""
        payload = dict(self.valid_payload)
        payload["confidence"] = 1.05
        with self.assertRaises(ValueError):
            Event.from_dict(payload)

        payload["confidence"] = -0.1
        with self.assertRaises(ValueError):
            Event.from_dict(payload)

    def test_source_must_be_data_demo_simulator(self) -> None:
        """source for this simulator must strictly be 'data_demo_simulator'."""
        payload = dict(self.valid_payload)
        payload["source"] = "unknown_source"
        with self.assertRaises(ValueError):
            Event.from_dict(payload)

    def test_raw_and_road_aligned_coordinates_separate(self) -> None:
        """Preserve original GNSS coordinates separately from road-aligned coordinates."""
        event = Event.from_dict(self.valid_payload)
        self.assertNotEqual(event.latitude, event.road_aligned_latitude)
        self.assertNotEqual(event.longitude, event.road_aligned_longitude)


if __name__ == "__main__":
    unittest.main()
