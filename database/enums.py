"""Enumeration types and constants for the database and fleet fusion modules.

Strictly aligned with docs/api-contract.md and docs/database.md.
"""

from enum import Enum


class EventType(str, Enum):
    """Allowed defect / civic risk event types."""

    POTHOLE = "POTHOLE"
    GARBAGE = "GARBAGE"
    TRAFFIC_OBSTRUCTION = "TRAFFIC_OBSTRUCTION"
    PEDESTRIAN_RISK = "PEDESTRIAN_RISK"


class Severity(str, Enum):
    """Event and incident severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConnectivityState(str, Enum):
    """Edge connectivity state at the time of event generation."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class IncidentStatus(str, Enum):
    """Fleet-fused incident lifecycle states."""

    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    RESOLUTION_CANDIDATE = "RESOLUTION_CANDIDATE"
    RESOLVED = "RESOLVED"


class TicketStatus(str, Enum):
    """Civic authority ticket lifecycle states."""

    REPORTED = "REPORTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class Department(str, Enum):
    """Responsible municipal departments."""

    MUNICIPAL_CORPORATION = "MUNICIPAL_CORPORATION"
    ROAD_AUTHORITY = "ROAD_AUTHORITY"
    SOLID_WASTE_MANAGEMENT = "SOLID_WASTE_MANAGEMENT"
    TRAFFIC_POLICE = "TRAFFIC_POLICE"


DEFAULT_DEPARTMENT_ROUTING = {
    EventType.POTHOLE.value: Department.ROAD_AUTHORITY.value,
    EventType.GARBAGE.value: Department.SOLID_WASTE_MANAGEMENT.value,
    EventType.TRAFFIC_OBSTRUCTION.value: Department.TRAFFIC_POLICE.value,
    EventType.PEDESTRIAN_RISK.value: Department.MUNICIPAL_CORPORATION.value,
}
