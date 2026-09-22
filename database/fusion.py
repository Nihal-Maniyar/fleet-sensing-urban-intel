"""Simple, deterministic Fleet Fusion policy implementation.

This module implements a spatial-temporal fusion policy using the existing
database models and operations. The policy is intentionally straightforward
and explainable:

- Spatial radius: 15 meters
- Time window: 5 minutes (300 seconds)
- Confidence threshold: 0.80 (observations below this are ignored for fusion)
- No ML, no fabrication, observations are preserved

Functions are idempotent where possible and use existing repository helpers
from `database.operations` and spatial helpers from `database.spatial`.
"""

from __future__ import annotations

import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from database.identifiers import generate_incident_id
from database.models import Incident, Observation
from database.operations import (
    create_or_update_incident,
    link_observation_to_incident,
)
from database.spatial import find_incidents_near


# Policy defaults
DEFAULT_RADIUS_METERS = 15.0
DEFAULT_TIME_WINDOW_SECONDS = 5 * 60
DEFAULT_CONFIDENCE_THRESHOLD = 0.80


def _next_incident_id(session: Session) -> str:
    """Generate a simple next incident id based on current count.

    Note: This is a pragmatic helper for the prototype tests and uses
    (count + 1). In a concurrent production system a proper sequence should
    be used.
    """
    count = session.query(Incident).count()
    return generate_incident_id(count + 1)


def fuse_observation(
    session: Session,
    observation: Observation,
    *,
    radius_meters: float = DEFAULT_RADIUS_METERS,
    time_window_seconds: int = DEFAULT_TIME_WINDOW_SECONDS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> Optional[Tuple[Incident, bool]]:
    """Fuse a single observation into an existing incident or create one.

    Returns a tuple of (incident, created_flag) when an incident is created or
    updated, or `None` when the observation is not eligible for fusion
    (e.g. confidence below threshold).

    Behavior and decisions (explicit and simple):
    - Observations with `confidence < confidence_threshold` are preserved
      but not used to create or update incidents.
    - Only observations with matching `event_type` are considered for fusion.
    - Spatial proximity is checked using `find_incidents_near` (PostGIS when
      available, haversine fallback in tests).
    - Temporal compatibility requires the candidate incident's
      `last_observed_at` to be within `time_window_seconds` of the
      observation's `timestamp`.
    - If multiple candidate incidents exist, the nearest is chosen.
    - Incident attributes are updated deterministically: centroid is a simple
      average weighted by observation counts, `confidence` is the max of
      existing and new observation confidence, and counts are incremented.

    The function is idempotent: if the observation is already linked to an
    incident, it returns that incident without creating duplicates.
    """

    # Preserve original observation; do not fuse if below confidence threshold
    if observation.confidence < confidence_threshold:
        return None

    # If already linked, return existing incident (idempotency)
    if observation.incident_associations:
        existing_inc = observation.incident_associations[0].incident
        return existing_inc, False

    # Choose geometry to use: prefer road-aligned if present
    lat = observation.road_aligned_latitude if observation.road_aligned_latitude is not None else observation.latitude
    lon = observation.road_aligned_longitude if observation.road_aligned_longitude is not None else observation.longitude

    # Find nearby incidents of the same event type
    candidates = find_incidents_near(
        session,
        latitude=lat,
        longitude=lon,
        radius_meters=radius_meters,
        event_type=observation.event_type,
        active_only=True,
    )

    # Filter by temporal window
    def _within_time_window(inc: Incident) -> bool:
        delta = abs((observation.timestamp - inc.last_observed_at).total_seconds())
        return delta <= time_window_seconds

    temporal_candidates = [(inc, dist) for inc, dist in candidates if _within_time_window(inc)]

    # Select nearest candidate if any
    if temporal_candidates:
        temporal_candidates.sort(key=lambda x: x[1])
        incident, _dist = temporal_candidates[0]

        # Recompute aggregated values
        new_obs_count = incident.observation_count + 1

        # Determine if this observation's bus is new for this incident
        existing_bus_ids = {
            assoc.observation.bus_id for assoc in incident.incident_associations
        }
        new_bus_count = incident.bus_count + (0 if observation.bus_id in existing_bus_ids else 1)

        # Centroid: simple running average by observations
        new_lat = (incident.latitude * incident.observation_count + observation.latitude) / new_obs_count
        new_lon = (incident.longitude * incident.observation_count + observation.longitude) / new_obs_count

        new_confidence = max(incident.confidence, observation.confidence)
        new_first = incident.first_observed_at
        new_last = max(incident.last_observed_at, observation.timestamp)

        updated_incident, created_flag = create_or_update_incident(
            session=session,
            incident_id=incident.incident_id,
            event_type=incident.event_type,
            latitude=new_lat,
            longitude=new_lon,
            confidence=new_confidence,
            severity=incident.severity,
            department=incident.department,
            first_observed_at=new_first,
            last_observed_at=new_last,
            observation_count=new_obs_count,
            bus_count=new_bus_count,
            status=incident.status,
        )

        # Link observation to incident (idempotent)
        link_observation_to_incident(session, updated_incident.incident_id, observation.observation_id)
        return updated_incident, created_flag

    # No candidate found -> create a new incident
    new_incident_id = _next_incident_id(session)
    created_incident, created_flag = create_or_update_incident(
        session=session,
        incident_id=new_incident_id,
        event_type=observation.event_type,
        latitude=observation.latitude,
        longitude=observation.longitude,
        confidence=observation.confidence,
        severity=observation.severity or "MEDIUM",
        department="MUNICIPAL_CORPORATION",
        first_observed_at=observation.timestamp,
        last_observed_at=observation.timestamp,
        observation_count=1,
        bus_count=1,
        status="CANDIDATE",
    )

    link_observation_to_incident(session, created_incident.incident_id, observation.observation_id)
    return created_incident, True
