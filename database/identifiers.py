"""Standardized identifier validators and generators according to docs/api-contract.md."""

from __future__ import annotations

import datetime
import re

BUS_ID_PATTERN = re.compile(r"^BUS-\d{3,}$")
EVENT_ID_PATTERN = re.compile(r"^EVT-\d{6}$")
OBSERVATION_ID_PATTERN = re.compile(r"^OBS-\d{6}$")
INCIDENT_ID_PATTERN = re.compile(r"^INC-\d{6}$")
TICKET_ID_PATTERN = re.compile(r"^POT-\d{4}-\d{6}$")
WORKORDER_ID_PATTERN = re.compile(r"^WO-\d{4}-\d{6}$")


def validate_bus_id(bus_id: str) -> bool:
    """Validate bus ID format: BUS-001, BUS-002, etc."""
    return bool(BUS_ID_PATTERN.match(bus_id))


def validate_event_id(event_id: str) -> bool:
    """Validate event ID format: EVT-000001, etc."""
    return bool(EVENT_ID_PATTERN.match(event_id))


def validate_observation_id(obs_id: str) -> bool:
    """Validate observation ID format: OBS-000001, etc."""
    return bool(OBSERVATION_ID_PATTERN.match(obs_id))


def validate_incident_id(inc_id: str) -> bool:
    """Validate incident ID format: INC-000001, etc."""
    return bool(INCIDENT_ID_PATTERN.match(inc_id))


def validate_ticket_id(ticket_id: str) -> bool:
    """Validate civic ticket ID format: POT-YYYY-XXXXXX."""
    return bool(TICKET_ID_PATTERN.match(ticket_id))


def validate_workorder_id(workorder_id: str) -> bool:
    """Validate work order ID format: WO-YYYY-XXXXXX."""
    return bool(WORKORDER_ID_PATTERN.match(workorder_id))


def generate_bus_id(number: int) -> str:
    """Generate a bus identifier, e.g. BUS-001."""
    return f"BUS-{number:03d}"


def generate_event_id(seq: int) -> str:
    """Generate an event identifier, e.g. EVT-000001."""
    return f"EVT-{seq:06d}"


def generate_observation_id(seq: int) -> str:
    """Generate an observation identifier, e.g. OBS-000001."""
    return f"OBS-{seq:06d}"


def generate_incident_id(seq: int) -> str:
    """Generate an incident identifier, e.g. INC-000001."""
    return f"INC-{seq:06d}"


def generate_ticket_id(seq: int, year: int | None = None) -> str:
    """Generate a civic ticket identifier, e.g. POT-2026-000001."""
    if year is None:
        year = datetime.datetime.now(datetime.timezone.utc).year
    return f"POT-{year:04d}-{seq:06d}"


def generate_workorder_id(seq: int, year: int | None = None) -> str:
    """Generate a work order identifier, e.g. WO-2026-000001."""
    if year is None:
        year = datetime.datetime.now(datetime.timezone.utc).year
    return f"WO-{year:04d}-{seq:06d}"
