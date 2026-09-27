"""Data access and repository operations providing idempotent ingestion and audit updates."""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional, Tuple, Union

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.enums import ConnectivityState, IncidentStatus, TicketStatus
from database.identifiers import (
    validate_bus_id,
    validate_event_id,
    validate_incident_id,
    validate_observation_id,
    validate_ticket_id,
)
from database.models import (
    Bus,
    Event,
    Incident,
    IncidentObservation,
    Observation,
    Ticket,
    TicketStatusHistory,
)
from database.types import point_to_wkt


def get_or_create_bus(
    session: Session,
    bus_id: str,
    route_id: Optional[str] = None,
    is_active: bool = True,
) -> Tuple[Bus, bool]:
    """Retrieve existing bus by ID or insert a new one."""
    if not validate_bus_id(bus_id):
        raise ValueError(f"Invalid bus_id format: '{bus_id}'. Expected BUS-XXX.")

    bus = session.get(Bus, bus_id)
    if bus is not None:
        if route_id and bus.route_id != route_id:
            bus.route_id = route_id
        bus.is_active = is_active
        bus.last_heartbeat_at = datetime.datetime.now(datetime.timezone.utc)
        return bus, False

    bus = Bus(
        bus_id=bus_id,
        route_id=route_id,
        is_active=is_active,
        last_heartbeat_at=datetime.datetime.now(datetime.timezone.utc),
    )
    session.add(bus)
    session.flush()
    return bus, True


def insert_event_idempotent(
    session: Session,
    event_data: Union[Dict[str, Any], Event],
) -> Tuple[Event, bool]:
    """Idempotently insert an edge event.

    If an event with the same `event_id` already exists, returns the existing record
    without raising an error and without creating a duplicate.

    Returns:
        (Event, created: bool)
    """
    if isinstance(event_data, Event):
        event_id = event_data.event_id
        bus_id = event_data.bus_id
        source = event_data.source
        connectivity_state = event_data.connectivity_state
        raw_payload = event_data.raw_payload
    else:
        event_id = event_data["event_id"]
        bus_id = event_data["bus_id"]
        source = event_data.get("source", "data_demo_simulator")
        connectivity_state = event_data.get("connectivity_state", ConnectivityState.ONLINE.value)
        raw_payload = event_data.get("raw_payload", event_data)

    if not validate_event_id(event_id):
        raise ValueError(f"Invalid event_id format: '{event_id}'. Expected EVT-XXXXXX.")

    # Check if already ingested (idempotency check)
    existing = session.get(Event, event_id)
    if existing is not None:
        return existing, False

    # Ensure foreign key parent bus exists
    get_or_create_bus(session, bus_id=bus_id)

    new_event = Event(
        event_id=event_id,
        bus_id=bus_id,
        source=source,
        connectivity_state=connectivity_state,
        raw_payload=raw_payload,
    )

    try:
        session.add(new_event)
        session.flush()
        return new_event, True
    except IntegrityError:
        session.rollback()
        existing = session.get(Event, event_id)
        if existing is not None:
            return existing, False
        raise


def create_observation(
    session: Session,
    observation_id: str,
    event_id: str,
    bus_id: str,
    event_type: str,
    timestamp: datetime.datetime,
    latitude: float,
    longitude: float,
    confidence: float,
    evidence_image: str,
    road_aligned_latitude: Optional[float] = None,
    road_aligned_longitude: Optional[float] = None,
    severity: Optional[str] = None,
    heading_degrees: Optional[float] = None,
) -> Observation:
    """Create and persist a normalized observation from an event."""
    if not validate_observation_id(observation_id):
        raise ValueError(f"Invalid observation_id '{observation_id}'. Expected OBS-XXXXXX.")

    # Calculate WKT geometries
    geom_raw = point_to_wkt(latitude, longitude)
    geom_road_aligned = (
        point_to_wkt(road_aligned_latitude, road_aligned_longitude)
        if road_aligned_latitude is not None and road_aligned_longitude is not None
        else None
    )

    observation = Observation(
        observation_id=observation_id,
        event_id=event_id,
        bus_id=bus_id,
        event_type=event_type,
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        road_aligned_latitude=road_aligned_latitude,
        road_aligned_longitude=road_aligned_longitude,
        geom_raw=geom_raw,
        geom_road_aligned=geom_road_aligned,
        confidence=confidence,
        severity=severity,
        evidence_image=evidence_image,
        heading_degrees=heading_degrees,
    )
    session.add(observation)
    session.flush()
    return observation


def link_observation_to_incident(
    session: Session,
    incident_id: str,
    observation_id: str,
) -> Tuple[IncidentObservation, bool]:
    """Link an observation to a fused incident in the audit junction table."""
    existing = session.get(IncidentObservation, (incident_id, observation_id))
    if existing is not None:
        return existing, False

    link = IncidentObservation(
        incident_id=incident_id,
        observation_id=observation_id,
        linked_at=datetime.datetime.now(datetime.timezone.utc),
    )
    session.add(link)
    session.flush()
    return link, True


def create_or_update_incident(
    session: Session,
    incident_id: str,
    event_type: str,
    latitude: float,
    longitude: float,
    confidence: float,
    severity: str,
    department: str,
    first_observed_at: datetime.datetime,
    last_observed_at: datetime.datetime,
    observation_count: int = 1,
    bus_count: int = 1,
    status: str = IncidentStatus.CANDIDATE.value,
) -> Tuple[Incident, bool]:
    """Create or update a fused incident."""
    if not validate_incident_id(incident_id):
        raise ValueError(f"Invalid incident_id '{incident_id}'. Expected INC-XXXXXX.")

    incident = session.get(Incident, incident_id)
    if incident is not None:
        incident.observation_count = observation_count
        incident.bus_count = bus_count
        incident.confidence = confidence
        incident.severity = severity
        incident.department = department
        incident.status = status
        incident.last_observed_at = last_observed_at
        incident.latitude = latitude
        incident.longitude = longitude
        incident.geom = point_to_wkt(latitude, longitude)
        session.flush()
        return incident, False

    incident = Incident(
        incident_id=incident_id,
        event_type=event_type,
        status=status,
        latitude=latitude,
        longitude=longitude,
        geom=point_to_wkt(latitude, longitude),
        observation_count=observation_count,
        bus_count=bus_count,
        confidence=confidence,
        severity=severity,
        department=department,
        first_observed_at=first_observed_at,
        last_observed_at=last_observed_at,
    )
    session.add(incident)
    session.flush()
    return incident, True


def create_ticket(
    session: Session,
    ticket_id: str,
    incident_id: str,
    event_type: str,
    department: str,
    google_maps_url: Optional[str] = None,
    workorder_id: Optional[str] = None,
    estimated_repair_sla_hours: int = 48,
    status: str = TicketStatus.REPORTED.value,
    created_by: str = "system",
    notes: Optional[str] = None,
) -> Ticket:
    """Create a civic ticket for a verified incident and record the initial history."""
    if not validate_ticket_id(ticket_id):
        raise ValueError(f"Invalid ticket_id '{ticket_id}'. Expected POT-YYYY-XXXXXX.")

    ticket = Ticket(
        ticket_id=ticket_id,
        incident_id=incident_id,
        workorder_id=workorder_id,
        event_type=event_type,
        status=status,
        department=department,
        google_maps_url=google_maps_url,
        estimated_repair_sla_hours=estimated_repair_sla_hours,
    )
    session.add(ticket)

    # Record initial audit entry
    history = TicketStatusHistory(
        ticket_id=ticket_id,
        from_status=None,
        to_status=status,
        changed_by=created_by,
        notes=notes or f"Ticket created with initial status {status}",
    )
    session.add(history)
    session.flush()
    return ticket


def transition_ticket_status(
    session: Session,
    ticket_id: str,
    new_status: str,
    changed_by: str,
    workorder_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> Ticket:
    """Transition a ticket to a new status and record the status transition in history."""
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket '{ticket_id}' not found.")

    old_status = ticket.status
    if old_status == new_status:
        return ticket

    ticket.status = new_status
    if workorder_id:
        ticket.workorder_id = workorder_id

    history = TicketStatusHistory(
        ticket_id=ticket_id,
        from_status=old_status,
        to_status=new_status,
        changed_by=changed_by,
        notes=notes,
    )
    session.add(history)
    session.flush()
    return ticket
