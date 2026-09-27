"""End-to-end Integration Pipeline test suite for Member 6.

Validates the complete vertical slice from:
Data/Test/Demo Simulator -> FastAPI Event Ingestion -> Observation Normalization ->
Offline SQLite WAL Buffering & Replay -> Incident Linking -> Ticket Lifecycle ->
Resolution Verification.

Strictly aligned with docs/demo.md, docs/api-contract.md, and docs/data-flow.md.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import (
    app,
    events_by_id,
    incidents_by_id,
    observations_by_id,
    tickets_by_id,
)
from scenarios.connectivity_outage import ConnectivityOutageScenario
from scenarios.dual_bus_pothole import DualBusPotholeScenario
from scenarios.resolution_verification import ResolutionVerificationScenario


class TestIntegrationPipeline(unittest.TestCase):
    """Integration test suite executing the target demonstration flow."""

    def setUp(self) -> None:
        # Reset backend in-memory storage before each integration test
        events_by_id.clear()
        observations_by_id.clear()
        incidents_by_id.clear()
        tickets_by_id.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        events_by_id.clear()
        observations_by_id.clear()
        incidents_by_id.clear()
        tickets_by_id.clear()

    def test_01_simulator_to_backend_dual_bus_corroboration(self) -> None:
        """Step 1 & 2 of demo: Two buses observe same pothole and backend persists observations."""
        scenario = DualBusPotholeScenario(auto_generate_evidence=True)
        events = scenario.generate_events()
        self.assertEqual(len(events), 2)

        evt1, evt2 = events[0], events[1]

        # 1. Ingest Observation from BUS-001
        resp1 = self.client.post("/events", json=evt1.to_dict())
        self.assertEqual(resp1.status_code, 201)
        self.assertFalse(resp1.json()["duplicate"])
        self.assertEqual(resp1.json()["event_id"], "EVT-000001")

        # 2. Ingest Observation from BUS-002
        resp2 = self.client.post("/events", json=evt2.to_dict())
        self.assertEqual(resp2.status_code, 201)
        self.assertFalse(resp2.json()["duplicate"])
        self.assertEqual(resp2.json()["event_id"], "EVT-000002")

        # 3. Verify both observations are normalized and stored
        obs_list = self.client.get("/observations")
        self.assertEqual(obs_list.status_code, 200)
        self.assertEqual(obs_list.json()["count"], 2)

        obs1 = self.client.get("/observations/OBS-000001").json()
        obs2 = self.client.get("/observations/OBS-000002").json()

        # Corroboration verification
        self.assertEqual(obs1["event_type"], "POTHOLE")
        self.assertEqual(obs2["event_type"], "POTHOLE")
        self.assertEqual(obs1["road_aligned_latitude"], obs2["road_aligned_latitude"])
        self.assertEqual(obs1["road_aligned_longitude"], obs2["road_aligned_longitude"])
        self.assertEqual(obs1["bus_id"], "BUS-001")
        self.assertEqual(obs2["bus_id"], "BUS-002")

        # Verify evidence files exist on disk
        self.assertTrue(os.path.exists(obs1["evidence_image"]))
        self.assertTrue(os.path.exists(obs2["evidence_image"]))

    def test_02_connectivity_outage_sqlite_wal_replay(self) -> None:
        """Step 3 of demo: Network outage, SQLite WAL buffering, reconnection, and idempotent replay."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "integration_edge_outbox.db")
            scenario = ConnectivityOutageScenario(
                base_sequence=3, auto_generate_evidence=True, db_path=db_path
            )
            events = scenario.generate_events()
            online_evt, offline_evt = events[0], events[1]

            # 1. Bus is ONLINE: event sent directly to backend
            resp1 = self.client.post("/events", json=online_evt.to_dict())
            self.assertEqual(resp1.status_code, 201)

            # 2. Bus drops offline: event stored into SQLite WAL queue
            scenario.outbox.enqueue(offline_evt)
            self.assertEqual(scenario.outbox.count_pending(), 1)

            # 3. Bus reconnects: retrieve pending from outbox and replay to backend
            pending_events = scenario.outbox.get_pending()
            self.assertEqual(len(pending_events), 1)
            replayed_evt = pending_events[0]

            # Replay event to backend
            replay_resp = self.client.post("/events", json=replayed_evt.to_dict())
            self.assertEqual(replay_resp.status_code, 201)
            self.assertFalse(replay_resp.json()["duplicate"])
            self.assertEqual(replay_resp.json()["event_id"], offline_evt.event_id)

            # Mark replayed in SQLite outbox
            scenario.outbox.mark_replayed(replayed_evt.event_id)
            self.assertEqual(scenario.outbox.count_pending(), 0)

            # 4. Replay AGAIN to verify idempotency
            dup_resp = self.client.post("/events", json=replayed_evt.to_dict())
            self.assertEqual(dup_resp.status_code, 201)
            self.assertTrue(dup_resp.json()["duplicate"])
            self.assertIn("Duplicate event ignored", dup_resp.json()["message"])

            # Backend count remains 2 (online + offline, no duplicate)
            self.assertEqual(self.client.get("/events").json()["count"], 2)

    def test_03_incident_and_ticket_lifecycle(self) -> None:
        """Step 4 of demo: Verified incident triggers civic ticket with lifecycle transitions."""
        # 1. Register verified incident from corroborated observations
        incident_payload = {
            "incident_id": "INC-000001",
            "event_type": "POTHOLE",
            "status": "VERIFIED",
            "latitude": 18.5196,
            "longitude": 73.8436,
            "observation_count": 2,
            "bus_count": 2,
            "confidence": 0.93,
            "severity": "HIGH",
            "department": "MUNICIPAL_CORPORATION",
            "first_observed_at": "2026-09-20T10:30:00Z",
            "last_observed_at": "2026-09-20T10:34:20Z",
        }
        inc_resp = self.client.post("/incidents", json=incident_payload)
        self.assertEqual(inc_resp.status_code, 201)

        # 2. Create civic ticket
        ticket_payload = {
            "ticket_id": "POT-2026-000001",
            "incident_id": "INC-000001",
            "workorder_id": "WO-2026-000001",
            "event_type": "POTHOLE",
            "confidence": 0.93,
            "latitude": 18.5196,
            "longitude": 73.8436,
            "evidence_image": "runtime/evidence/EVT-000001.jpg",
            "google_maps_url": "https://www.google.com/maps/dir/?api=1&destination=18.5196,73.8436",
            "estimated_repair_sla_hours": 48,
            "status": "REPORTED",
            "created_at": "2026-09-20T10:36:00Z",
            "updated_at": "2026-09-20T10:36:00Z",
        }
        tkt_resp = self.client.post("/tickets", json=ticket_payload)
        self.assertEqual(tkt_resp.status_code, 201)

        # 3. Verify Google Maps navigation link
        map_resp = self.client.get("/tickets/POT-2026-000001/map")
        self.assertEqual(map_resp.status_code, 200)
        self.assertIn("destination=18.5196,73.8436", map_resp.json()["google_maps_url"])

        # 4. Lifecycle status progression
        for next_st in ("ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"):
            patch_resp = self.client.patch(
                f"/tickets/POT-2026-000001/status?new_status={next_st}"
            )
            self.assertEqual(patch_resp.status_code, 200)
            self.assertEqual(patch_resp.json()["ticket"]["status"], next_st)

    def test_04_resolution_verification_evidence(self) -> None:
        """Step 5 of demo: Later bus observation captures post-repair evidence."""
        scenario = ResolutionVerificationScenario(
            base_sequence=20, auto_generate_evidence=True
        )
        events = scenario.generate_events()
        before_evt, after_evt = events[0], events[1]

        # Ingest before and after events
        self.client.post("/events", json=before_evt.to_dict())
        self.client.post("/events", json=after_evt.to_dict())

        obs_before = self.client.get("/observations/OBS-000020").json()
        obs_after = self.client.get("/observations/OBS-000021").json()

        # Both agree on exact road position
        self.assertEqual(
            obs_before["road_aligned_latitude"], obs_after["road_aligned_latitude"]
        )
        self.assertEqual(
            obs_before["road_aligned_longitude"], obs_after["road_aligned_longitude"]
        )

        # Before is defect, After is repaired
        self.assertEqual(obs_before["severity"], "HIGH")
        self.assertEqual(obs_after["severity"], "LOW")

        # Confirm evidence files exist
        self.assertTrue(os.path.exists(obs_before["evidence_image"]))
        self.assertTrue(os.path.exists(obs_after["evidence_image"]))


if __name__ == "__main__":
    unittest.main()
