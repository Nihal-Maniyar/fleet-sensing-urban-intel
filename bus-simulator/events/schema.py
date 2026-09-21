"""Contract-compliant Event schema for the Actual Bus Simulator.

Strictly aligned with docs/api-contract.md.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

EVENT_ID_PATTERN = re.compile(r"^EVT-\d{6}$")
BUS_ID_PATTERN = re.compile(r"^BUS-\d{3,}$")
ISO8601_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")

ALLOWED_EVENT_TYPES = {
    "POTHOLE",
    "GARBAGE",
    "TRAFFIC_OBSTRUCTION",
    "PEDESTRIAN_RISK",
}

ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH"}
ALLOWED_CONNECTIVITY_STATES = {"ONLINE", "OFFLINE"}


@dataclass
class Event:
    """Represents a contract-valid edge/simulator event payload.

    Mandatory fields:
        event_id, bus_id, event_type, timestamp, latitude, longitude,
        confidence, evidence_image, source
    Optional v1 fields:
        road_aligned_latitude, road_aligned_longitude, heading_degrees,
        route_id, severity, connectivity_state
    """

    event_id: str
    bus_id: str
    event_type: str
    timestamp: str
    latitude: float
    longitude: float
    confidence: float
    evidence_image: str
    source: str = "actual_bus_simulator"
    road_aligned_latitude: Optional[float] = None
    road_aligned_longitude: Optional[float] = None
    heading_degrees: Optional[float] = None
    route_id: Optional[str] = None
    severity: Optional[str] = None
    connectivity_state: Optional[str] = "ONLINE"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate payload against official API contract rules in docs/api-contract.md."""
        if not EVENT_ID_PATTERN.match(self.event_id):
            raise ValueError(
                f"Invalid event_id '{self.event_id}'. Must match EVT-XXXXXX format (e.g. EVT-000001)."
            )

        if not BUS_ID_PATTERN.match(self.bus_id):
            raise ValueError(
                f"Invalid bus_id '{self.bus_id}'. Must match BUS-XXX format (e.g. BUS-001)."
            )

        if self.event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{self.event_type}'. Must be one of {sorted(ALLOWED_EVENT_TYPES)}."
            )

        if not ISO8601_UTC_PATTERN.match(self.timestamp):
            raise ValueError(
                f"Invalid timestamp '{self.timestamp}'. Must be ISO 8601 UTC ending in 'Z' (e.g. 2026-09-20T10:30:00Z)."
            )

        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"latitude {self.latitude} is out of WGS84 range [-90, 90].")

        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"longitude {self.longitude} is out of WGS84 range [-180, 180].")

        if self.road_aligned_latitude is not None and not (-90.0 <= self.road_aligned_latitude <= 90.0):
            raise ValueError(f"road_aligned_latitude {self.road_aligned_latitude} out of range [-90, 90].")

        if self.road_aligned_longitude is not None and not (-180.0 <= self.road_aligned_longitude <= 180.0):
            raise ValueError(f"road_aligned_longitude {self.road_aligned_longitude} out of range [-180, 180].")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence {self.confidence} must be between 0.0 and 1.0.")

        if not self.evidence_image:
            raise ValueError("evidence_image reference cannot be empty.")

        if self.source != "actual_bus_simulator":
            raise ValueError(
                f"Invalid source '{self.source}'. For this simulator, source must be 'actual_bus_simulator'."
            )

        if self.severity is not None and self.severity not in ALLOWED_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{self.severity}'. Must be one of {sorted(ALLOWED_SEVERITIES)}."
            )

        if self.connectivity_state is not None and self.connectivity_state not in ALLOWED_CONNECTIVITY_STATES:
            raise ValueError(
                f"Invalid connectivity_state '{self.connectivity_state}'. Must be 'ONLINE' or 'OFFLINE'."
            )

        if self.heading_degrees is not None and not (0.0 <= self.heading_degrees <= 360.0):
            raise ValueError(f"heading_degrees {self.heading_degrees} must be between 0.0 and 360.0.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary preserving non-null contract fields in canonical order."""
        data = asdict(self)
        result: Dict[str, Any] = {}
        ordered_keys = [
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
        ]
        for key in ordered_keys:
            val = data.get(key)
            if val is not None:
                result[key] = val
        return result

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize event to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Event:
        """Create and validate Event from dictionary."""
        return cls(
            event_id=data["event_id"],
            bus_id=data["bus_id"],
            event_type=data["event_type"],
            timestamp=data["timestamp"],
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            confidence=float(data["confidence"]),
            evidence_image=data["evidence_image"],
            source=data.get("source", "actual_bus_simulator"),
            road_aligned_latitude=float(data["road_aligned_latitude"]) if data.get("road_aligned_latitude") is not None else None,
            road_aligned_longitude=float(data["road_aligned_longitude"]) if data.get("road_aligned_longitude") is not None else None,
            heading_degrees=float(data["heading_degrees"]) if data.get("heading_degrees") is not None else None,
            route_id=data.get("route_id"),
            severity=data.get("severity"),
            connectivity_state=data.get("connectivity_state", "ONLINE"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> Event:
        """Create Event from JSON string."""
        return cls.from_dict(json.loads(json_str))
