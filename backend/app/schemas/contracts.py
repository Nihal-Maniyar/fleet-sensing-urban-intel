"""Contract Pydantic schemas strictly aligned with docs/api-contract.md."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

EVENT_TYPES = {
    "POTHOLE",
    "GARBAGE",
    "TRAFFIC_OBSTRUCTION",
    "PEDESTRIAN_RISK",
}

SOURCES = {
    "actual_bus_simulator",
    "data_demo_simulator",
    "future_real_edge_device",
}

SEVERITIES = {"LOW", "MEDIUM", "HIGH"}
CONNECTIVITY_STATES = {"ONLINE", "OFFLINE"}

INCIDENT_STATUSES = {
    "CANDIDATE",
    "VERIFIED",
    "REJECTED",
    "RESOLUTION_CANDIDATE",
    "RESOLVED",
}

TICKET_STATUSES = {
    "REPORTED",
    "ACKNOWLEDGED",
    "IN_PROGRESS",
    "RESOLVED",
}


# ---------------------------------------------------------------------------
# Pydantic models - names match docs/api-contract.md
# ---------------------------------------------------------------------------

class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(pattern=r"^EVT-\d{6}$")
    bus_id: str = Field(pattern=r"^BUS-\d{3,}$")
    event_type: str
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    road_aligned_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    road_aligned_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    heading_degrees: Optional[float] = Field(default=None, ge=0, le=360)
    route_id: Optional[str] = None

    confidence: float = Field(ge=0.0, le=1.0)
    severity: Optional[str] = None
    evidence_image: str
    source: str
    connectivity_state: Optional[str] = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError(
                f"event_type must be one of: {', '.join(sorted(EVENT_TYPES))}"
            )
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SEVERITIES:
            raise ValueError("severity must be LOW, MEDIUM, or HIGH")
        return value

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value not in SOURCES:
            raise ValueError(
                "source must be actual_bus_simulator, "
                "data_demo_simulator, or future_real_edge_device"
            )
        return value

    @field_validator("connectivity_state")
    @classmethod
    def validate_connectivity(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in CONNECTIVITY_STATES:
            raise ValueError("connectivity_state must be ONLINE or OFFLINE")
        return value


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(pattern=r"^OBS-\d{6}$")
    event_id: str = Field(pattern=r"^EVT-\d{6}$")
    bus_id: str = Field(pattern=r"^BUS-\d{3,}$")
    event_type: str
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Optional[str] = None
    evidence_image: str
    road_aligned_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    road_aligned_longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class Incident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(pattern=r"^INC-\d{6}$")
    event_type: str
    status: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    observation_count: int = Field(ge=0)
    bus_count: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    severity: str
    department: str
    first_observed_at: datetime
    last_observed_at: datetime

    @field_validator("event_type")
    @classmethod
    def validate_incident_event_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError(
                f"event_type must be one of: {', '.join(sorted(EVENT_TYPES))}"
            )
        return value

    @field_validator("status")
    @classmethod
    def validate_incident_status(cls, value: str) -> str:
        if value not in INCIDENT_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(INCIDENT_STATUSES))}"
            )
        return value

    @field_validator("severity")
    @classmethod
    def validate_incident_severity(cls, value: str) -> str:
        if value not in SEVERITIES:
            raise ValueError("severity must be LOW, MEDIUM, or HIGH")
        return value


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(pattern=r"^[A-Z]+-\d{4}-\d{6}$")
    incident_id: str = Field(pattern=r"^INC-\d{6}$")
    workorder_id: Optional[str] = Field(
        default=None,
        pattern=r"^WO-\d{4}-\d{6}$",
    )
    event_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    evidence_image: str
    google_maps_url: str
    estimated_repair_sla_hours: int = Field(ge=0)
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("event_type")
    @classmethod
    def validate_ticket_event_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError(
                f"event_type must be one of: {', '.join(sorted(EVENT_TYPES))}"
            )
        return value

    @field_validator("status")
    @classmethod
    def validate_ticket_status(cls, value: str) -> str:
        if value not in TICKET_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(TICKET_STATUSES))}"
            )
        return value
