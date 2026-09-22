"""FastAPI backend application for Fleet Sensing Urban Intelligence."""

from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, status
import os

# Optional database integration: if DATABASE_URL is set and the database
# package is importable, use the DB-backed ingestion flow which persists
# observations and runs fleet fusion. Otherwise continue using the in-memory
# prototype storage to avoid breaking existing tests and demos.
try:
    from database.connection import db_session
    from database.operations import insert_event_idempotent, create_observation
    from database.fusion import fuse_observation
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

# Handle imports whether launched from root or backend directory
try:
    from backend.app.schemas.contracts import (
        EVENT_TYPES,
        INCIDENT_STATUSES,
        SEVERITIES,
        SOURCES,
        TICKET_STATUSES,
        Event,
        Incident,
        Observation,
        Ticket,
    )
except ImportError:
    from app.schemas.contracts import (
        EVENT_TYPES,
        INCIDENT_STATUSES,
        SEVERITIES,
        SOURCES,
        TICKET_STATUSES,
        Event,
        Incident,
        Observation,
        Ticket,
    )


app = FastAPI(
    title="Fleet Sensing Urban Intelligence - Backend",
    version="1.0.0",
    description="FastAPI service for contract-valid event ingestion, observations, incidents, and civic ticket lifecycle.",
)

# ---------------------------------------------------------------------------
# Prototype in-memory storage
# ---------------------------------------------------------------------------
# In-memory storage for prototype integration.
# Future milestone attaches PostgreSQL/PostGIS at this boundary.
events_by_id: dict[str, dict] = {}
observations_by_id: dict[str, dict] = {}
incidents_by_id: dict[str, dict] = {}
tickets_by_id: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iso_utc(value: datetime) -> str:
    """Return ISO 8601 UTC with a trailing Z."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def event_to_storage(event: Event) -> dict:
    data = event.model_dump(mode="json")
    data["timestamp"] = iso_utc(event.timestamp)
    return data


def create_observation_from_event(event: Event, incoming_timestamp: str) -> dict:
    """Derive a normalized immutable Observation record from an ingested Event."""
    # Match OBS-XXXXXX with EVT-XXXXXX sequence suffix
    seq = event.event_id.split("-")[-1]
    obs_id = f"OBS-{seq}"
    return {
        "observation_id": obs_id,
        "event_id": event.event_id,
        "bus_id": event.bus_id,
        "event_type": event.event_type,
        "timestamp": incoming_timestamp,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "confidence": event.confidence,
        "severity": event.severity,
        "evidence_image": event.evidence_image,
        "road_aligned_latitude": event.road_aligned_latitude,
        "road_aligned_longitude": event.road_aligned_longitude,
    }


# ---------------------------------------------------------------------------
# Router for API endpoints (mounted at both "/" and "/api/v1")
# ---------------------------------------------------------------------------

api_router = APIRouter()


# ---------------------------------------------------------------------------
# Health / Metadata
# ---------------------------------------------------------------------------

@api_router.get("/", tags=["Health"])
@api_router.get("/health", tags=["Health"])
def health_check():
    return {
        "service": "Member 3 Backend",
        "status": "running",
        "contract_version": "v1",
        "timestamp": iso_utc(datetime.now(timezone.utc)),
    }


# ---------------------------------------------------------------------------
# Event Ingestion
# ---------------------------------------------------------------------------

@api_router.post("/events", status_code=status.HTTP_201_CREATED, tags=["Events"])
def ingest_event(event: Event):
    """
    Validate and idempotently ingest one contract-valid event.

    Replaying an existing event_id does not create a second record.
    The stored event and associated observation are immutable for this prototype.
    """
    # If a real database is available and configured via DATABASE_URL,
    # use the DB-backed flow: persist event, create observation, run fusion.
    incoming = event_to_storage(event)

    if DB_AVAILABLE and os.environ.get("DATABASE_URL"):
        try:
            with db_session() as db:
                evt, created = insert_event_idempotent(db, event)

                # If event already exists, verify payload equality for idempotent replay
                if not created:
                    # For DB-backed flow we return the existing record summary
                    return {
                        "message": "Duplicate event ignored (idempotent replay)",
                        "event_id": event.event_id,
                        "duplicate": True,
                        "event": {"event_id": evt.event_id},
                    }

                # Persist normalized observation using DB operations
                seq = event.event_id.split("-")[-1]
                obs_id = f"OBS-{seq}"
                obs = create_observation(
                    db,
                    observation_id=obs_id,
                    event_id=event.event_id,
                    bus_id=event.bus_id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    latitude=event.latitude,
                    longitude=event.longitude,
                    road_aligned_latitude=event.road_aligned_latitude,
                    road_aligned_longitude=event.road_aligned_longitude,
                    confidence=event.confidence,
                    evidence_image=event.evidence_image,
                    severity=event.severity,
                    heading_degrees=event.heading_degrees if hasattr(event, "heading_degrees") else None,
                )

                # Run fleet fusion on the newly created observation
                fused = fuse_observation(db, obs)

                resp = {
                    "message": "Event accepted",
                    "event_id": event.event_id,
                    "duplicate": False,
                    "event": {"event_id": evt.event_id},
                }
                if fused is not None:
                    inc, inc_created = fused
                    resp["fusion"] = {"incident_id": inc.incident_id, "created": inc_created}

                return resp
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive fallback
            # If DB path fails for any reason, return a 500 to signal the issue.
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    # Fallback prototype in-memory flow (unchanged)
    if event.event_id in events_by_id:
        existing = events_by_id[event.event_id]

        # Same event_id + different payload is a conflict, not a duplicate.
        if existing != incoming:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"event_id {event.event_id} already exists with a different payload"
                ),
            )

        return {
            "message": "Duplicate event ignored (idempotent replay)",
            "event_id": event.event_id,
            "duplicate": True,
            "event": existing,
        }

    events_by_id[event.event_id] = incoming

    # Record normalized observation record
    obs = create_observation_from_event(event, incoming["timestamp"])
    observations_by_id[obs["observation_id"]] = obs

    return {
        "message": "Event accepted",
        "event_id": event.event_id,
        "duplicate": False,
        "event": incoming,
    }


@api_router.get("/events", tags=["Events"])
def list_events():
    return {
        "count": len(events_by_id),
        "events": list(events_by_id.values()),
    }


@api_router.get("/events/{event_id}", tags=["Events"])
def get_event(event_id: str):
    event = events_by_id.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


# ---------------------------------------------------------------------------
# Observation read API
# ---------------------------------------------------------------------------

@api_router.get("/observations", tags=["Observations"])
def list_observations():
    return {
        "count": len(observations_by_id),
        "observations": list(observations_by_id.values()),
    }


@api_router.get("/observations/{observation_id}", tags=["Observations"])
def get_observation(observation_id: str):
    observation = observations_by_id.get(observation_id)
    if observation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observation not found")
    return observation


# ---------------------------------------------------------------------------
# Incident API
# ---------------------------------------------------------------------------

@api_router.post("/incidents", status_code=status.HTTP_201_CREATED, tags=["Incidents"])
def create_incident(incident: Incident):
    data = incident.model_dump(mode="json")
    data["first_observed_at"] = iso_utc(incident.first_observed_at)
    data["last_observed_at"] = iso_utc(incident.last_observed_at)

    if incident.incident_id in incidents_by_id:
        existing = incidents_by_id[incident.incident_id]
        if existing != data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"incident_id {incident.incident_id} already exists "
                    "with a different payload"
                ),
            )
        return {
            "message": "Duplicate incident ignored",
            "incident": existing,
            "duplicate": True,
        }

    incidents_by_id[incident.incident_id] = data

    return {
        "message": "Incident accepted",
        "incident": data,
        "duplicate": False,
    }


@api_router.get("/incidents", tags=["Incidents"])
def list_incidents():
    return {
        "count": len(incidents_by_id),
        "incidents": list(incidents_by_id.values()),
    }


@api_router.get("/incidents/{incident_id}", tags=["Incidents"])
def get_incident(incident_id: str):
    incident = incidents_by_id.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


# ---------------------------------------------------------------------------
# Ticket API
# ---------------------------------------------------------------------------

@api_router.post("/tickets", status_code=status.HTTP_201_CREATED, tags=["Tickets"])
def create_ticket(ticket: Ticket):
    data = ticket.model_dump(mode="json")
    data["created_at"] = iso_utc(ticket.created_at)
    data["updated_at"] = iso_utc(ticket.updated_at)

    if ticket.ticket_id in tickets_by_id:
        existing = tickets_by_id[ticket.ticket_id]
        if existing != data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"ticket_id {ticket.ticket_id} already exists "
                    "with a different payload"
                ),
            )
        return {
            "message": "Duplicate ticket ignored",
            "ticket": existing,
            "duplicate": True,
        }

    tickets_by_id[ticket.ticket_id] = data

    return {
        "message": "Ticket accepted",
        "ticket": data,
        "duplicate": False,
    }


@api_router.get("/tickets", tags=["Tickets"])
def list_tickets():
    return {
        "count": len(tickets_by_id),
        "tickets": list(tickets_by_id.values()),
    }


@api_router.get("/tickets/{ticket_id}", tags=["Tickets"])
def get_ticket(ticket_id: str):
    ticket = tickets_by_id.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@api_router.patch("/tickets/{ticket_id}/status", tags=["Tickets"])
def update_ticket_status(ticket_id: str, new_status: str):
    if new_status not in TICKET_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid ticket status. Allowed: "
                + ", ".join(sorted(TICKET_STATUSES))
            ),
        )

    ticket = tickets_by_id.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    ticket["status"] = new_status
    ticket["updated_at"] = iso_utc(datetime.now(timezone.utc))

    return {
        "message": "Ticket status updated",
        "ticket": ticket,
    }


@api_router.get("/tickets/{ticket_id}/map", tags=["Tickets"])
def get_ticket_map(ticket_id: str):
    ticket = tickets_by_id.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    latitude = ticket["latitude"]
    longitude = ticket["longitude"]
    google_maps_url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&destination={latitude},{longitude}"
    )

    return {
        "ticket_id": ticket_id,
        "latitude": latitude,
        "longitude": longitude,
        "google_maps_url": google_maps_url,
    }


# Mount routes at root and with /api/v1 prefix
app.include_router(api_router)
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
