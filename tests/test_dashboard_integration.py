"""Tests for GIS Dashboard integration and contract conformance."""

from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from backend.app.main import app, tickets_by_id


class TestDashboardIntegration(unittest.TestCase):
    """Verify GIS dashboard file validity, contract compliance, and backend delivery."""

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.repo_root = Path(__file__).resolve().parent.parent
        self.dashboard_html = self.repo_root / "dashboard" / "index.html"

    def test_dashboard_file_exists_and_valid(self) -> None:
        self.assertTrue(self.dashboard_html.is_file(), "dashboard/index.html must exist")
        content = self.dashboard_html.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("Fleet Sensing Urban Intel", content)
        # Contract compliance checks
        self.assertIn("INC-000001", content)
        self.assertIn("POT-2026-", content)
        self.assertIn("BUS-001", content)
        self.assertIn("REPORTED", content)
        self.assertIn("ACKNOWLEDGED", content)
        self.assertIn("IN_PROGRESS", content)
        self.assertIn("RESOLVED", content)
        self.assertIn("google.com/maps", content)
        self.assertIn("Pune", content)

    def test_dashboard_served_via_fastapi(self) -> None:
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Fleet Sensing Urban Intel", response.text)

    def test_dashboard_linked_in_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("dashboard_url"), "/dashboard")

    def test_dashboard_ticket_lifecycle_backend_sync(self) -> None:
        # Create a sample ticket
        ticket_payload = {
            "ticket_id": "POT-2026-999999",
            "incident_id": "INC-000001",
            "workorder_id": "WO-2026-999999",
            "event_type": "POTHOLE",
            "confidence": 0.94,
            "latitude": 18.5204,
            "longitude": 73.8567,
            "evidence_image": "runtime/evidence/EVT-000001.jpg",
            "google_maps_url": "https://www.google.com/maps/dir/?api=1&destination=18.5204,73.8567",
            "estimated_repair_sla_hours": 48,
            "status": "REPORTED",
            "created_at": "2026-09-20T10:30:00Z",
            "updated_at": "2026-09-20T10:30:00Z",
        }
        res = self.client.post("/tickets", json=ticket_payload)
        self.assertEqual(res.status_code, 201)

        # Transition through lifecycle matching the frontend order
        lifecycle = ["ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"]
        for st in lifecycle:
            patch_res = self.client.patch(f"/tickets/POT-2026-999999/status?new_status={st}")
            self.assertEqual(patch_res.status_code, 200)
            self.assertEqual(patch_res.json()["ticket"]["status"], st)

        # Cleanup
        tickets_by_id.pop("POT-2026-999999", None)
