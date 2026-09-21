"""Comprehensive database test suite covering schema, relationships, idempotency, and spatial queries.

Strictly aligned with docs/database.md, docs/api-contract.md, and AGENTS.md.
"""

from __future__ import annotations

import datetime
import unittest

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database.connection import init_db
from database.enums import (
    ConnectivityState,
    Department,
    EventType,
    IncidentStatus,
    Severity,
    TicketStatus,
)
from database.identifiers import (
    generate_bus_id,
    generate_event_id,
    generate_incident_id,
    generate_observation_id,
    generate_ticket_id,
    generate_workorder_id,
    validate_bus_id,
    validate_event_id,
    validate_incident_id,
    validate_observation_id,
    validate_ticket_id,
    validate_workorder_id,
)
from database.models import (
    Base,
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
from database.seed import seed_database
from database.spatial import (
    find_incidents_near,
    find_observations_near,
    haversine_distance_meters,
    query_incidents_in_bbox,
    query_observations_in_bbox,
)


class TestDatabaseLayer(unittest.TestCase):
    """Test suite executing on an in-memory SQLite engine with PostGIS-compatible abstractions."""

    def setUp(self) -> None:
        self.engine = sa.create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session: Session = self.Session()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_01_table_creation_and_schema(self) -> None:
        """Verify all 7 required core tables exist in the schema."""
        inspector = sa.inspect(self.engine)
        table_names = set(inspector.get_table_names())
        expected_tables = {
            "buses",
            "events",
            "observations",
            "incidents",
            "incident_observations",
            "tickets",
            "ticket_status_history",
        }
        self.assertTrue(expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}")

    def test_02_identifier_validation_and_generation(self) -> None:
        """Verify ID format validation and generation matches project contracts."""
        # Valid IDs
        self.assertTrue(validate_bus_id("BUS-001"))
        self.assertTrue(validate_event_id("EVT-000001"))
        self.assertTrue(validate_observation_id("OBS-000001"))
        self.assertTrue(validate_incident_id("INC-000001"))
        self.assertTrue(validate_ticket_id("POT-2026-000001"))
        self.assertTrue(validate_workorder_id("WO-2026-000001"))

        # Invalid IDs
        self.assertFalse(validate_bus_id("bus_1"))
        self.assertFalse(validate_event_id("EVENT-1"))
        self.assertFalse(validate_observation_id("12345"))
        self.assertFalse(validate_incident_id("INC-1"))
        self.assertFalse(validate_ticket_id("TICKET-2026-1"))
        self.assertFalse(validate_workorder_id("WORKORDER-1"))

        # Generator checks
        self.assertEqual(generate_bus_id(1), "BUS-001")
        self.assertEqual(generate_event_id(1), "EVT-000001")
        self.assertEqual(generate_observation_id(1), "OBS-000001")
        self.assertEqual(generate_incident_id(1), "INC-000001")
        self.assertEqual(generate_ticket_id(1, year=2026), "POT-2026-000001")
        self.assertEqual(generate_workorder_id(1, year=2026), "WO-2026-000001")

    def test_03_bus_creation_and_relationships(self) -> None:
        """Verify Bus creation and parent-child relationship to events."""
        bus, created = get_or_create_bus(self.session, "BUS-001", route_id="ROUTE-A")
        self.assertTrue(created)
        self.assertEqual(bus.bus_id, "BUS-001")
        self.assertTrue(bus.is_active)

        # Retrieve existing bus
        bus_dup, created_dup = get_or_create_bus(self.session, "BUS-001", route_id="ROUTE-B")
        self.assertFalse(created_dup)
        self.assertEqual(bus_dup.route_id, "ROUTE-B")

    def test_04_event_idempotency(self) -> None:
        """Verify that duplicate events (e.g. from offline MQTT replay) are ingested idempotently."""
        event_data = {
            "event_id": "EVT-000001",
            "bus_id": "BUS-001",
            "source": "actual_bus_simulator",
            "connectivity_state": ConnectivityState.ONLINE.value,
            "raw_payload": {"confidence": 0.9},
        }

        # First ingestion
        evt, created = insert_event_idempotent(self.session, event_data)
        self.assertTrue(created)
        self.assertEqual(evt.event_id, "EVT-000001")

        # Second ingestion with same event_id (replay)
        evt_replayed, replayed_created = insert_event_idempotent(self.session, event_data)
        self.assertFalse(replayed_created)
        self.assertEqual(evt_replayed.event_id, "EVT-000001")

        # Confirm exactly 1 record in database
        count = self.session.query(Event).filter_by(event_id="EVT-000001").count()
        self.assertEqual(count, 1)

        # Confirm direct duplicate insert raises IntegrityError on a fresh session
        self.session.expunge_all()
        dup_event = Event(
            event_id="EVT-000001",
            bus_id="BUS-001",
            source="actual_bus_simulator",
        )
        self.session.add(dup_event)
        with self.assertRaises(IntegrityError):
            self.session.flush()
        self.session.rollback()

    def test_05_observation_creation_and_coordinate_preservation(self) -> None:
        """Verify raw coordinates and road-aligned coordinates are preserved separately."""
        insert_event_idempotent(
            self.session,
            {
                "event_id": "EVT-000002",
                "bus_id": "BUS-001",
                "source": "data_demo_simulator",
            },
        )

        obs = create_observation(
            self.session,
            observation_id="OBS-000001",
            event_id="EVT-000002",
            bus_id="BUS-001",
            event_type=EventType.POTHOLE.value,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            latitude=18.520420,
            longitude=73.856710,
            road_aligned_latitude=18.520400,
            road_aligned_longitude=73.856700,
            confidence=0.91,
            severity=Severity.HIGH.value,
            evidence_image="runtime/evidence/EVT-000002.jpg",
            heading_degrees=90.0,
        )

        # Verify raw GPS coordinates are NOT overwritten by road-aligned coordinates
        self.assertEqual(obs.latitude, 18.520420)
        self.assertEqual(obs.longitude, 73.856710)
        self.assertEqual(obs.road_aligned_latitude, 18.520400)
        self.assertEqual(obs.road_aligned_longitude, 73.856700)
        self.assertNotEqual((obs.latitude, obs.longitude), (obs.road_aligned_latitude, obs.road_aligned_longitude))

        # Verify geometries are set
        self.assertIsNotNone(obs.geom_raw)
        self.assertIsNotNone(obs.geom_road_aligned)

        # Unique event_id constraint on observations
        with self.assertRaises(IntegrityError):
            create_observation(
                self.session,
                observation_id="OBS-000002",
                event_id="EVT-000002",  # Duplicate event_id
                bus_id="BUS-001",
                event_type=EventType.POTHOLE.value,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                latitude=18.520420,
                longitude=73.856710,
                confidence=0.95,
                evidence_image="runtime/evidence/dup.jpg",
            )
        self.session.rollback()

    def test_06_incident_observation_linking(self) -> None:
        """Verify observations from multiple buses are linked to one incident."""
        now = datetime.datetime.now(datetime.timezone.utc)

        # Create two events from separate buses
        insert_event_idempotent(self.session, {"event_id": "EVT-000010", "bus_id": "BUS-001", "source": "sim"})
        insert_event_idempotent(self.session, {"event_id": "EVT-000011", "bus_id": "BUS-002", "source": "sim"})

        obs1 = create_observation(
            self.session, "OBS-000010", "EVT-000010", "BUS-001",
            EventType.POTHOLE.value, now, 18.5204, 73.8567, 0.90, "img1.jpg"
        )
        obs2 = create_observation(
            self.session, "OBS-000011", "EVT-000011", "BUS-002",
            EventType.POTHOLE.value, now, 18.5205, 73.8568, 0.95, "img2.jpg"
        )

        inc, created = create_or_update_incident(
            self.session,
            incident_id="INC-000001",
            event_type=EventType.POTHOLE.value,
            latitude=18.52045,
            longitude=73.85675,
            confidence=0.96,
            severity=Severity.HIGH.value,
            department=Department.ROAD_AUTHORITY.value,
            first_observed_at=now,
            last_observed_at=now,
            observation_count=2,
            bus_count=2,
            status=IncidentStatus.VERIFIED.value,
        )
        self.assertTrue(created)

        link1, created1 = link_observation_to_incident(self.session, "INC-000001", "OBS-000010")
        link2, created2 = link_observation_to_incident(self.session, "INC-000001", "OBS-000011")
        self.assertTrue(created1)
        self.assertTrue(created2)

        # Duplicate link is idempotent
        _, dup_link_created = link_observation_to_incident(self.session, "INC-000001", "OBS-000010")
        self.assertFalse(dup_link_created)

        # Verify incident has both associations
        fetched_inc = self.session.get(Incident, "INC-000001")
        self.assertIsNotNone(fetched_inc)
        self.assertEqual(len(fetched_inc.incident_associations), 2)
        linked_obs_ids = {a.observation_id for a in fetched_inc.incident_associations}
        self.assertEqual(linked_obs_ids, {"OBS-000010", "OBS-000011"})

    def test_07_ticket_creation_and_lifecycle_history(self) -> None:
        """Verify ticket creation and status history transitions."""
        now = datetime.datetime.now(datetime.timezone.utc)

        # Create verified incident first
        create_or_update_incident(
            self.session,
            incident_id="INC-000005",
            event_type=EventType.POTHOLE.value,
            latitude=18.5204,
            longitude=73.8567,
            confidence=0.93,
            severity=Severity.HIGH.value,
            department=Department.ROAD_AUTHORITY.value,
            first_observed_at=now,
            last_observed_at=now,
            status=IncidentStatus.VERIFIED.value,
        )

        # Create ticket
        ticket = create_ticket(
            self.session,
            ticket_id="POT-2026-000001",
            incident_id="INC-000005",
            event_type=EventType.POTHOLE.value,
            department=Department.ROAD_AUTHORITY.value,
            google_maps_url="https://www.google.com/maps/dir/?api=1&destination=18.5204,73.8567",
            status=TicketStatus.REPORTED.value,
            created_by="system_fusion",
            notes="Initial ticket generation",
        )
        self.assertEqual(ticket.status, TicketStatus.REPORTED.value)

        # Advance status: REPORTED -> ACKNOWLEDGED
        transition_ticket_status(
            self.session,
            ticket_id="POT-2026-000001",
            new_status=TicketStatus.ACKNOWLEDGED.value,
            changed_by="pmc_admin",
            notes="Acknowledged by road authority",
        )

        # Advance status: ACKNOWLEDGED -> IN_PROGRESS with work order
        transition_ticket_status(
            self.session,
            ticket_id="POT-2026-000001",
            new_status=TicketStatus.IN_PROGRESS.value,
            changed_by="contractor",
            workorder_id="WO-2026-000001",
            notes="Work order dispatched",
        )

        # Advance status: IN_PROGRESS -> RESOLVED
        transition_ticket_status(
            self.session,
            ticket_id="POT-2026-000001",
            new_status=TicketStatus.RESOLVED.value,
            changed_by="inspector",
            notes="Pothole repaired and inspected",
        )

        # Check final status and history audit entries
        refreshed_ticket = self.session.get(Ticket, "POT-2026-000001")
        self.assertIsNotNone(refreshed_ticket)
        self.assertEqual(refreshed_ticket.status, TicketStatus.RESOLVED.value)
        self.assertEqual(refreshed_ticket.workorder_id, "WO-2026-000001")

        history = (
            self.session.query(TicketStatusHistory)
            .filter_by(ticket_id="POT-2026-000001")
            .order_by(TicketStatusHistory.id)
            .all()
        )
        self.assertEqual(len(history), 4)
        statuses = [(h.from_status, h.to_status) for h in history]
        self.assertEqual(
            statuses,
            [
                (None, "REPORTED"),
                ("REPORTED", "ACKNOWLEDGED"),
                ("ACKNOWLEDGED", "IN_PROGRESS"),
                ("IN_PROGRESS", "RESOLVED"),
            ],
        )

    def test_08_spatial_proximity_query_15_meters(self) -> None:
        """Verify spatial search within 15 meters."""
        now = datetime.datetime.now(datetime.timezone.utc)

        # Base point: Pune FC Road (18.520400, 73.856700)
        base_lat, base_lon = 18.520400, 73.856700

        # Inc 1: Exact base point (0 meters)
        create_or_update_incident(
            self.session, "INC-000021", EventType.POTHOLE.value,
            base_lat, base_lon, 0.9, Severity.HIGH.value, Department.ROAD_AUTHORITY.value,
            now, now, status=IncidentStatus.VERIFIED.value
        )

        # Inc 2: Approx 8 meters away (~0.00007 deg lat)
        inc2_lat, inc2_lon = 18.520470, 73.856700
        dist_inc2 = haversine_distance_meters(base_lat, base_lon, inc2_lat, inc2_lon)
        self.assertLess(dist_inc2, 15.0)
        create_or_update_incident(
            self.session, "INC-000022", EventType.POTHOLE.value,
            inc2_lat, inc2_lon, 0.85, Severity.HIGH.value, Department.ROAD_AUTHORITY.value,
            now, now, status=IncidentStatus.VERIFIED.value
        )

        # Inc 3: JM Road ~900 meters away
        inc3_lat, inc3_lon = 18.528300, 73.850100
        dist_inc3 = haversine_distance_meters(base_lat, base_lon, inc3_lat, inc3_lon)
        self.assertGreater(dist_inc3, 500.0)
        create_or_update_incident(
            self.session, "INC-000023", EventType.POTHOLE.value,
            inc3_lat, inc3_lon, 0.85, Severity.MEDIUM.value, Department.ROAD_AUTHORITY.value,
            now, now, status=IncidentStatus.VERIFIED.value
        )

        # Query near base point with 15 meter radius
        nearby = find_incidents_near(self.session, base_lat, base_lon, radius_meters=15.0)
        nearby_ids = [inc.incident_id for inc, _ in nearby]

        self.assertIn("INC-000021", nearby_ids)
        self.assertIn("INC-000022", nearby_ids)
        self.assertNotIn("INC-000023", nearby_ids)

    def test_09_bounding_box_query(self) -> None:
        """Verify bounding box queries filter incidents within the viewport."""
        now = datetime.datetime.now(datetime.timezone.utc)

        # Inside Pune Central (Shivajinagar/Deccan): lat [18.51, 18.54], lon [73.84, 73.87]
        create_or_update_incident(
            self.session, "INC-000031", EventType.POTHOLE.value,
            18.5204, 73.8567, 0.9, Severity.HIGH.value, Department.ROAD_AUTHORITY.value,
            now, now, status=IncidentStatus.VERIFIED.value
        )
        create_or_update_incident(
            self.session, "INC-000032", EventType.GARBAGE.value,
            18.5283, 73.8501, 0.8, Severity.MEDIUM.value, Department.SOLID_WASTE_MANAGEMENT.value,
            now, now, status=IncidentStatus.CANDIDATE.value
        )

        # Far Outside: Katraj (lat 18.45, lon 73.86)
        create_or_update_incident(
            self.session, "INC-000033", EventType.TRAFFIC_OBSTRUCTION.value,
            18.4500, 73.8600, 0.8, Severity.LOW.value, Department.TRAFFIC_POLICE.value,
            now, now, status=IncidentStatus.VERIFIED.value
        )

        in_bbox = query_incidents_in_bbox(
            self.session,
            min_lat=18.51,
            min_lon=73.84,
            max_lat=18.54,
            max_lon=73.87,
        )
        in_bbox_ids = {inc.incident_id for inc in in_bbox}
        self.assertIn("INC-000031", in_bbox_ids)
        self.assertIn("INC-000032", in_bbox_ids)
        self.assertNotIn("INC-000033", in_bbox_ids)

    def test_10_seed_database_execution(self) -> None:
        """Verify the demo Pune seed script populates required records cleanly."""
        seed_database(self.session)

        # Verify buses
        self.assertGreaterEqual(self.session.query(Bus).count(), 3)
        # Verify events & observations
        self.assertGreaterEqual(self.session.query(Event).count(), 3)
        self.assertGreaterEqual(self.session.query(Observation).count(), 3)
        # Verify candidate and verified incidents
        cand_count = self.session.query(Incident).filter_by(status=IncidentStatus.CANDIDATE.value).count()
        verif_count = self.session.query(Incident).filter_by(status=IncidentStatus.VERIFIED.value).count()
        self.assertGreaterEqual(cand_count, 1)
        self.assertGreaterEqual(verif_count, 1)
        # Verify ticket and status history
        self.assertGreaterEqual(self.session.query(Ticket).count(), 1)
        self.assertGreaterEqual(self.session.query(TicketStatusHistory).count(), 3)


if __name__ == "__main__":
    unittest.main()
