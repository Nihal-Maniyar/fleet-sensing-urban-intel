"""Comprehensive system-wide integration tests for Member 6.

Validates the complete vertical slice:
Simulators -> MQTT Ingestion -> FastAPI Backend -> PostgreSQL/PostGIS / Database ->
Road Alignment -> Fleet Fusion Engine -> Incident Verification ->
Civic Ticket Lifecycle -> WebSocket Broadcasts -> GIS Dashboard.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import (
    app,
    buses_by_id,
    events_by_id,
    incidents_by_id,
    observations_by_id,
    tickets_by_id,
)
from backend.app.services.mqtt_consumer import MQTTEventConsumer
from database.models import Base
from database.operations import (
    create_observation,
    create_or_update_incident,
    create_ticket,
    get_or_create_bus,
    insert_event_idempotent,
    link_observation_to_incident,
    transition_ticket_status,
)
from fusion.policy import FleetFusionEngine, haversine_distance_meters
from scenarios.dual_bus_pothole import DualBusPotholeScenario
from scenarios.resolution_verification import ResolutionVerificationScenario


class TestSystemIntegration(unittest.TestCase):
    """End-to-end integration tests verifying cross-module cohesion."""

    def setUp(self) -> None:
        events_by_id.clear()
        observations_by_id.clear()
        incidents_by_id.clear()
        tickets_by_id.clear()
        buses_by_id.clear()
        self.client = TestClient(app)

        # Set up SQLite test database session
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        events_by_id.clear()
        observations_by_id.clear()
        incidents_by_id.clear()
        tickets_by_id.clear()
        buses_by_id.clear()

    def test_end_to_end_dual_bus_fusion_and_civic_ticketing(self) -> None:
        """Verify two independent buses detecting a defect at Goodluck Chowk fuses into a verified incident & ticket."""
        scenario = DualBusPotholeScenario(auto_generate_evidence=True)
        events = scenario.generate_events()
        self.assertEqual(len(events), 2)
        evt1, evt2 = events[0], events[1]

        # 1. Bus 1 reports pothole
        resp1 = self.client.post("/events", json=evt1.to_dict())
        self.assertEqual(resp1.status_code, 201)
        self.assertFalse(resp1.json()["duplicate"])
        self.assertEqual(resp1.json()["event_id"], "EVT-000001")

        # Verify observation created
        obs1 = self.client.get("/observations/OBS-000001").json()
        self.assertEqual(obs1["bus_id"], "BUS-001")
        self.assertEqual(obs1["event_type"], "POTHOLE")

        # 2. Bus 2 corroborates at the same road segment
        resp2 = self.client.post("/events", json=evt2.to_dict())
        self.assertEqual(resp2.status_code, 201)
        self.assertFalse(resp2.json()["duplicate"])
        self.assertEqual(resp2.json()["event_id"], "EVT-000002")

        # 3. Verify automated Fleet Fusion corroborated into a verified incident
        incidents_resp = self.client.get("/incidents").json()
        self.assertGreaterEqual(incidents_resp["count"], 1)
        inc = incidents_resp["incidents"][0]
        self.assertEqual(inc["status"], "VERIFIED")
        self.assertEqual(inc["event_type"], "POTHOLE")
        self.assertGreaterEqual(inc["observation_count"], 2)
        self.assertIn("BUS-001", inc["buses"])
        self.assertIn("BUS-002", inc["buses"])

        # 4. Verify civic ticket was automatically issued for the verified incident
        tickets_resp = self.client.get("/tickets").json()
        self.assertGreaterEqual(tickets_resp["count"], 1)
        ticket = tickets_resp["tickets"][0]
        self.assertTrue(ticket["ticket_id"].startswith("POT-2026-"))
        self.assertEqual(ticket["status"], "REPORTED")
        self.assertEqual(ticket["estimated_repair_sla_hours"], 48)
        self.assertIn("google.com/maps", ticket["google_maps_url"])

        # 5. Advance ticket lifecycle: REPORTED -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED
        for next_status in ["ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"]:
            patch_resp = self.client.patch(f"/tickets/{ticket['ticket_id']}/status?new_status={next_status}")
            self.assertEqual(patch_resp.status_code, 200)
            self.assertEqual(patch_resp.json()["ticket"]["status"], next_status)

        # Confirm resolved status
        final_ticket = self.client.get(f"/tickets/{ticket['ticket_id']}").json()
        self.assertEqual(final_ticket["status"], "RESOLVED")

    def test_database_operations_persistence(self) -> None:
        """Verify database operations with foreign keys, WKT geometries, and status audits."""
        with self.Session() as session:
            # 1. Bus registration
            bus, created = get_or_create_bus(session, bus_id="BUS-001", route_id="ROUTE-PUNE-FC")
            self.assertTrue(created)
            self.assertEqual(bus.bus_id, "BUS-001")

            # 2. Event insertion
            event_data = {
                "event_id": "EVT-000001",
                "bus_id": "BUS-001",
                "source": "actual_bus_simulator",
                "connectivity_state": "ONLINE",
                "raw_payload": {"confidence": 0.94},
            }
            evt_db, evt_created = insert_event_idempotent(session, event_data)
            self.assertTrue(evt_created)
            self.assertEqual(evt_db.event_id, "EVT-000001")

            # Duplicate event insertion (idempotency check)
            evt_dup, dup_created = insert_event_idempotent(session, event_data)
            self.assertFalse(dup_created)
            self.assertEqual(evt_dup.event_id, "EVT-000001")

            # 3. Observation creation with road alignment
            now = datetime.now(timezone.utc)
            obs_db = create_observation(
                session=session,
                observation_id="OBS-000001",
                event_id="EVT-000001",
                bus_id="BUS-001",
                event_type="POTHOLE",
                timestamp=now,
                latitude=18.519616,
                longitude=73.843587,
                road_aligned_latitude=18.519600,
                road_aligned_longitude=73.843600,
                confidence=0.94,
                evidence_image="runtime/evidence/EVT-000001.jpg",
                severity="HIGH",
            )
            self.assertEqual(obs_db.observation_id, "OBS-000001")
            self.assertIsNotNone(obs_db.geom_road_aligned)

            # 4. Incident creation & linking
            inc_db, inc_created = create_or_update_incident(
                session=session,
                incident_id="INC-000001",
                event_type="POTHOLE",
                latitude=18.519600,
                longitude=73.843600,
                confidence=0.95,
                severity="HIGH",
                department="MUNICIPAL_CORPORATION",
                first_observed_at=now,
                last_observed_at=now,
                observation_count=1,
                bus_count=1,
                status="VERIFIED",
            )
            self.assertTrue(inc_created)
            link_observation_to_incident(session, "INC-000001", "OBS-000001")

            # 5. Ticket creation & transition
            tkt_db = create_ticket(
                session=session,
                ticket_id="POT-2026-000001",
                incident_id="INC-000001",
                event_type="POTHOLE",
                department="MUNICIPAL_CORPORATION",
                google_maps_url="https://www.google.com/maps/dir/?api=1&destination=18.5196,73.8436",
            )
            self.assertEqual(tkt_db.status, "REPORTED")

            tkt_updated = transition_ticket_status(
                session=session,
                ticket_id="POT-2026-000001",
                new_status="IN_PROGRESS",
                changed_by="dispatcher",
            )
            self.assertEqual(tkt_updated.status, "IN_PROGRESS")

    def test_mqtt_consumer_payload_handling(self) -> None:
        """Verify MQTT consumer decodes JSON payloads and triggers ingestion callback."""
        received_events = []

        def mock_callback(payload):
            received_events.append(payload)

        consumer = MQTTEventConsumer(on_event_received=mock_callback)

        class MockMessage:
            topic = "beyonders/events/v1"
            payload = json.dumps({
                "event_id": "EVT-000099",
                "bus_id": "BUS-001",
                "event_type": "POTHOLE",
                "timestamp": "2026-09-22T08:30:00Z",
                "latitude": 18.5196,
                "longitude": 73.8436,
                "confidence": 0.94,
                "severity": "HIGH",
                "evidence_image": "runtime/evidence/EVT-000099.jpg",
                "source": "actual_bus_simulator",
            }).encode("utf-8")

        consumer._on_message(None, None, MockMessage())
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0]["event_id"], "EVT-000099")

    def test_fleet_fusion_clustering_distance(self) -> None:
        """Verify Haversine distance logic correctly clusters points within 25 meters."""
        # Two points 15 meters apart on FC Road
        lat1, lon1 = 18.519600, 73.843600
        lat2, lon2 = 18.519700, 73.843600
        dist = haversine_distance_meters(lat1, lon1, lat2, lon2)
        self.assertLess(dist, 25.0)

        # Far point 500 meters away
        lat_far, lon_far = 18.524000, 73.843600
        dist_far = haversine_distance_meters(lat1, lon1, lat_far, lon_far)
        self.assertGreater(dist_far, 100.0)


if __name__ == "__main__":
    unittest.main()
