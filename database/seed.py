"""Seed script populating realistic Pune demonstration data into the database."""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy.orm import Session

from database.connection import SessionLocal, create_db_engine, db_session, init_db
from database.enums import (
    ConnectivityState,
    Department,
    EventType,
    IncidentStatus,
    Severity,
    TicketStatus,
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
from database.operations import (
    create_observation,
    create_or_update_incident,
    create_ticket,
    get_or_create_bus,
    insert_event_idempotent,
    link_observation_to_incident,
    transition_ticket_status,
)


def seed_database(session: Optional[Session] = None) -> None:
    """Populate database with demo Pune fleet observations, incidents, and tickets."""
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        ten_mins_ago = now - datetime.timedelta(minutes=10)
        six_mins_ago = now - datetime.timedelta(minutes=6)
        two_mins_ago = now - datetime.timedelta(minutes=2)

        print("[Seed] 1. Registering buses...")
        bus1, _ = get_or_create_bus(session, "BUS-001", route_id="ROUTE-FC-ROAD")
        bus2, _ = get_or_create_bus(session, "BUS-002", route_id="ROUTE-JM-ROAD")
        bus3, _ = get_or_create_bus(session, "BUS-003", route_id="ROUTE-KARVE-ROAD")
        session.commit()

        print("[Seed] 2. Inserting edge events & observations (Pune locations)...")
        # Event 1 (BUS-001): Pothole on Fergusson College (FC) Road, Pune
        evt1, _ = insert_event_idempotent(
            session,
            {
                "event_id": "EVT-000001",
                "bus_id": "BUS-001",
                "source": "data_demo_simulator",
                "connectivity_state": ConnectivityState.ONLINE.value,
                "raw_payload": {
                    "event_id": "EVT-000001",
                    "bus_id": "BUS-001",
                    "event_type": "POTHOLE",
                    "route": "FC Road",
                },
            },
        )
        if not session.get(Observation, "OBS-000001"):
            create_observation(
                session,
                observation_id="OBS-000001",
                event_id="EVT-000001",
                bus_id="BUS-001",
                event_type=EventType.POTHOLE.value,
                timestamp=ten_mins_ago,
                latitude=18.520420,
                longitude=73.856710,
                road_aligned_latitude=18.520400,
                road_aligned_longitude=73.856700,
                confidence=0.92,
                severity=Severity.HIGH.value,
                evidence_image="runtime/evidence/EVT-000001.jpg",
                heading_degrees=92.0,
            )

        # Event 2 (BUS-002): Same pothole corroborated by BUS-002 4 minutes later
        evt2, _ = insert_event_idempotent(
            session,
            {
                "event_id": "EVT-000002",
                "bus_id": "BUS-002",
                "source": "data_demo_simulator",
                "connectivity_state": ConnectivityState.ONLINE.value,
                "raw_payload": {
                    "event_id": "EVT-000002",
                    "bus_id": "BUS-002",
                    "event_type": "POTHOLE",
                    "route": "FC Road Corroboration",
                },
            },
        )
        if not session.get(Observation, "OBS-000002"):
            create_observation(
                session,
                observation_id="OBS-000002",
                event_id="EVT-000002",
                bus_id="BUS-002",
                event_type=EventType.POTHOLE.value,
                timestamp=six_mins_ago,
                latitude=18.520435,
                longitude=73.856725,
                road_aligned_latitude=18.520400,
                road_aligned_longitude=73.856700,
                confidence=0.95,
                severity=Severity.HIGH.value,
                evidence_image="runtime/evidence/EVT-000002.jpg",
                heading_degrees=95.0,
            )

        # Event 3 (BUS-003): Garbage accumulation on Jangli Maharaj (JM) Road, Pune
        evt3, _ = insert_event_idempotent(
            session,
            {
                "event_id": "EVT-000003",
                "bus_id": "BUS-003",
                "source": "data_demo_simulator",
                "connectivity_state": ConnectivityState.ONLINE.value,
                "raw_payload": {
                    "event_id": "EVT-000003",
                    "bus_id": "BUS-003",
                    "event_type": "GARBAGE",
                    "route": "JM Road",
                },
            },
        )
        if not session.get(Observation, "OBS-000003"):
            create_observation(
                session,
                observation_id="OBS-000003",
                event_id="EVT-000003",
                bus_id="BUS-003",
                event_type=EventType.GARBAGE.value,
                timestamp=two_mins_ago,
                latitude=18.528300,
                longitude=73.850100,
                road_aligned_latitude=18.528280,
                road_aligned_longitude=73.850120,
                confidence=0.78,
                severity=Severity.MEDIUM.value,
                evidence_image="runtime/evidence/EVT-000003.jpg",
                heading_degrees=180.0,
            )

        session.commit()

        print("[Seed] 3. Creating incidents (one verified, one candidate)...")
        # Incident 1: Verified Pothole Incident on FC Road (fused from OBS-000001 and OBS-000002)
        inc1, _ = create_or_update_incident(
            session,
            incident_id="INC-000001",
            event_type=EventType.POTHOLE.value,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.96,
            severity=Severity.HIGH.value,
            department=Department.ROAD_AUTHORITY.value,
            first_observed_at=ten_mins_ago,
            last_observed_at=six_mins_ago,
            observation_count=2,
            bus_count=2,
            status=IncidentStatus.VERIFIED.value,
        )
        link_observation_to_incident(session, "INC-000001", "OBS-000001")
        link_observation_to_incident(session, "INC-000001", "OBS-000002")

        # Incident 2: Candidate Garbage Incident on JM Road (single observation OBS-000003)
        inc2, _ = create_or_update_incident(
            session,
            incident_id="INC-000002",
            event_type=EventType.GARBAGE.value,
            latitude=18.528280,
            longitude=73.850120,
            confidence=0.78,
            severity=Severity.MEDIUM.value,
            department=Department.SOLID_WASTE_MANAGEMENT.value,
            first_observed_at=two_mins_ago,
            last_observed_at=two_mins_ago,
            observation_count=1,
            bus_count=1,
            status=IncidentStatus.CANDIDATE.value,
        )
        link_observation_to_incident(session, "INC-000002", "OBS-000003")
        session.commit()

        print("[Seed] 4. Creating civic ticket & status history for verified incident...")
        if not session.get(Ticket, "POT-2026-000001"):
            ticket = create_ticket(
                session,
                ticket_id="POT-2026-000001",
                incident_id="INC-000001",
                event_type=EventType.POTHOLE.value,
                department=Department.ROAD_AUTHORITY.value,
                google_maps_url="https://www.google.com/maps/dir/?api=1&destination=18.520400,73.856700",
                workorder_id="WO-2026-000001",
                estimated_repair_sla_hours=24,
                status=TicketStatus.REPORTED.value,
                created_by="system_fusion",
                notes="Incident verified by fleet fusion across BUS-001 and BUS-002.",
            )

            # Advance lifecycle: ACKNOWLEDGED -> IN_PROGRESS
            transition_ticket_status(
                session,
                ticket_id="POT-2026-000001",
                new_status=TicketStatus.ACKNOWLEDGED.value,
                changed_by="pmc_ward_officer",
                notes="Assigned to Shivajinagar road repair team.",
            )
            transition_ticket_status(
                session,
                ticket_id="POT-2026-000001",
                new_status=TicketStatus.IN_PROGRESS.value,
                changed_by="contractor_lead",
                workorder_id="WO-2026-000001",
                notes="Crew deployed with quick-setting cold-mix asphalt.",
            )

        session.commit()
        print("[Seed] Demo seed data successfully loaded into database!")

    except Exception as exc:
        session.rollback()
        print(f"[Seed] Error seeding database: {exc}")
        raise
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    seed_database()
