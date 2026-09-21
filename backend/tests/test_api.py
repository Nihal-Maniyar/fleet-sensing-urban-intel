"""Comprehensive API tests for event ingestion, observations, incidents, and tickets."""

from datetime import datetime, timezone
import pytest


@pytest.fixture
def sample_event_payload():
    return {
        "event_id": "EVT-000001",
        "bus_id": "BUS-001",
        "event_type": "POTHOLE",
        "timestamp": "2026-09-20T10:30:00Z",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "road_aligned_latitude": 18.5203,
        "road_aligned_longitude": 73.8568,
        "heading_degrees": 92.4,
        "route_id": "ROUTE-A",
        "confidence": 0.91,
        "severity": "HIGH",
        "evidence_image": "runtime/evidence/EVT-000001.jpg",
        "source": "data_demo_simulator",
        "connectivity_state": "ONLINE",
    }


def test_health_check(client):
    """Health endpoint returns service name and v1 contract."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["contract_version"] == "v1"

    # Root path also returns health
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert root_resp.json()["contract_version"] == "v1"


def test_ingest_event_success(client, sample_event_payload):
    """Valid event is ingested and creates a normalized observation."""
    response = client.post("/events", json=sample_event_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["duplicate"] is False
    assert body["event_id"] == "EVT-000001"
    assert body["event"]["bus_id"] == "BUS-001"

    # Query event by ID
    get_resp = client.get("/events/EVT-000001")
    assert get_resp.status_code == 200
    assert get_resp.json()["event_id"] == "EVT-000001"

    # Verify normalized observation was created
    obs_resp = client.get("/observations/OBS-000001")
    assert obs_resp.status_code == 200
    obs = obs_resp.json()
    assert obs["observation_id"] == "OBS-000001"
    assert obs["event_id"] == "EVT-000001"
    assert obs["bus_id"] == "BUS-001"
    assert obs["confidence"] == 0.91


def test_ingest_event_idempotent_replay(client, sample_event_payload):
    """Replaying an identical event is idempotent and does not create duplicate."""
    # First ingestion
    resp1 = client.post("/events", json=sample_event_payload)
    assert resp1.status_code == 201
    assert resp1.json()["duplicate"] is False

    # Second ingestion with same payload
    resp2 = client.post("/events", json=sample_event_payload)
    assert resp2.status_code == 201
    assert resp2.json()["duplicate"] is True
    assert "Duplicate event ignored" in resp2.json()["message"]

    # Count of events remains 1
    list_resp = client.get("/events")
    assert list_resp.json()["count"] == 1


def test_ingest_event_conflict(client, sample_event_payload):
    """Ingesting an existing event_id with a different payload raises 409 Conflict."""
    client.post("/events", json=sample_event_payload)

    altered_payload = dict(sample_event_payload)
    altered_payload["confidence"] = 0.50

    conflict_resp = client.post("/events", json=altered_payload)
    assert conflict_resp.status_code == 409
    assert "already exists with a different payload" in conflict_resp.json()["detail"]


def test_validation_errors(client, sample_event_payload):
    """Invalid event fields are rejected with 422 Unprocessable Entity."""
    # 1. Invalid event_id
    bad = dict(sample_event_payload, event_id="evt_01")
    assert client.post("/events", json=bad).status_code == 422

    # 2. Invalid bus_id
    bad = dict(sample_event_payload, bus_id="Bus01")
    assert client.post("/events", json=bad).status_code == 422

    # 3. Disallowed event_type
    bad = dict(sample_event_payload, event_type="ALIEN")
    assert client.post("/events", json=bad).status_code == 422

    # 4. Out of range latitude
    bad = dict(sample_event_payload, latitude=120.0)
    assert client.post("/events", json=bad).status_code == 422

    # 5. Out of range confidence
    bad = dict(sample_event_payload, confidence=1.5)
    assert client.post("/events", json=bad).status_code == 422

    # 6. Disallowed source
    bad = dict(sample_event_payload, source="unauthorized_source")
    assert client.post("/events", json=bad).status_code == 422

    # 7. Disallowed severity
    bad = dict(sample_event_payload, severity="CATASTROPHIC")
    assert client.post("/events", json=bad).status_code == 422

    # 8. Extra unexpected field
    bad = dict(sample_event_payload, unknown_field="test")
    assert client.post("/events", json=bad).status_code == 422


def test_dual_prefix_support(client, sample_event_payload):
    """Both /events and /api/v1/events routes function equivalently."""
    payload = dict(sample_event_payload, event_id="EVT-000002")
    resp = client.post("/api/v1/events", json=payload)
    assert resp.status_code == 201

    get_root = client.get("/events/EVT-000002")
    get_v1 = client.get("/api/v1/events/EVT-000002")
    assert get_root.status_code == 200
    assert get_v1.status_code == 200
    assert get_root.json() == get_v1.json()


def test_incidents_api(client):
    """Incidents can be created, retrieved, and listed."""
    incident_payload = {
        "incident_id": "INC-000001",
        "event_type": "POTHOLE",
        "status": "VERIFIED",
        "latitude": 18.5203,
        "longitude": 73.8568,
        "observation_count": 2,
        "bus_count": 2,
        "confidence": 0.93,
        "severity": "HIGH",
        "department": "MUNICIPAL_CORPORATION",
        "first_observed_at": "2026-09-20T10:30:00Z",
        "last_observed_at": "2026-09-20T10:35:00Z",
    }

    create_resp = client.post("/incidents", json=incident_payload)
    assert create_resp.status_code == 201
    assert create_resp.json()["duplicate"] is False

    # Retrieve by ID
    get_resp = client.get("/incidents/INC-000001")
    assert get_resp.status_code == 200
    assert get_resp.json()["incident_id"] == "INC-000001"
    assert get_resp.json()["status"] == "VERIFIED"

    # List all
    list_resp = client.get("/incidents")
    assert list_resp.json()["count"] == 1

    # Duplicate creation
    dup_resp = client.post("/incidents", json=incident_payload)
    assert dup_resp.status_code == 201
    assert dup_resp.json()["duplicate"] is True


def test_ticket_lifecycle_and_map(client):
    """Tickets follow REPORTED -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED and map generation."""
    ticket_payload = {
        "ticket_id": "POT-2026-000001",
        "incident_id": "INC-000001",
        "workorder_id": "WO-2026-000001",
        "event_type": "POTHOLE",
        "confidence": 0.93,
        "latitude": 18.5203,
        "longitude": 73.8568,
        "evidence_image": "runtime/evidence/EVT-000001.jpg",
        "google_maps_url": "https://www.google.com/maps/dir/?api=1&destination=18.5203,73.8568",
        "estimated_repair_sla_hours": 48,
        "status": "REPORTED",
        "created_at": "2026-09-20T10:36:00Z",
        "updated_at": "2026-09-20T10:36:00Z",
    }

    create_resp = client.post("/tickets", json=ticket_payload)
    assert create_resp.status_code == 201

    # Map endpoint generates Google Maps directions link
    map_resp = client.get("/tickets/POT-2026-000001/map")
    assert map_resp.status_code == 200
    map_data = map_resp.json()
    assert map_data["latitude"] == 18.5203
    assert map_data["longitude"] == 73.8568
    assert "destination=18.5203,73.8568" in map_data["google_maps_url"]

    # Valid lifecycle transitions
    for next_status in ("ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"):
        patch_resp = client.patch(
            f"/tickets/POT-2026-000001/status?new_status={next_status}"
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["ticket"]["status"] == next_status

    # Invalid status is rejected
    bad_status_resp = client.patch(
        "/tickets/POT-2026-000001/status?new_status=DISCARDED"
    )
    assert bad_status_resp.status_code == 400
    assert "Invalid ticket status" in bad_status_resp.json()["detail"]


def test_simulator_scenario_ingestion(client):
    """Events generated by Data/Test/Demo Simulator are accepted cleanly by Backend."""
    from scenarios.dual_bus_pothole import DualBusPotholeScenario
    from scenarios.master_demo import MasterDemoScenario

    scenario = DualBusPotholeScenario(auto_generate_evidence=False)
    events = scenario.generate_events()

    for evt in events:
        resp = client.post("/events", json=evt.to_dict())
        assert resp.status_code == 201
        assert resp.json()["event_id"] == evt.event_id

    # Check that observations were created for each simulator event
    list_obs = client.get("/observations")
    assert list_obs.status_code == 200
    assert list_obs.json()["count"] == len(events)

