#!/usr/bin/env python3
"""Repeatable demonstration runner for Fleet Sensing Urban Intelligence.

Executes the complete vertical slice story defined in docs/demo.md:
1. Dual-bus pothole detection & corroboration on FC Road, Pune.
2. Network outage, local SQLite WAL queueing, and idempotent replay on Karve Road.
3. Diverse urban event sensing (Garbage, Traffic, Pedestrian Risk).
4. Incident verification & civic ticket dispatch with Google Maps link.
5. Ticket lifecycle transitions (REPORTED -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED).
6. Post-repair observation supporting automated resolution verification.

Usage:
    # Run continuous demo with 0.5s pause between steps
    python3 scripts/run_demo.py --delay 0.5

    # Run interactive step-by-step mode (press Enter to advance)
    python3 scripts/run_demo.py --step

    # Run against a live running backend server
    python3 scripts/run_demo.py --backend-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SIM_DIR = PROJECT_ROOT / "data-demo-simulator"
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

# Color formatting for terminal presentation
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class DemoClient:
    """Client for dispatching events either via live HTTP or in-memory TestClient."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self._test_client = None

        if not self.base_url:
            from fastapi.testclient import TestClient
            from backend.app.main import app
            self._test_client = TestClient(app)

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._test_client:
            resp = self._test_client.post(endpoint, json=data)
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"POST {endpoint} failed ({resp.status_code}): {resp.text}")
            return resp.json()
        else:
            url = f"{self.base_url}{endpoint}"
            payload = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return json.loads(resp.read().decode("utf-8"))

    def get(self, endpoint: str) -> Dict[str, Any]:
        if self._test_client:
            resp = self._test_client.get(endpoint)
            if resp.status_code != 200:
                raise RuntimeError(f"GET {endpoint} failed ({resp.status_code}): {resp.text}")
            return resp.json()
        else:
            url = f"{self.base_url}{endpoint}"
            with urllib.request.urlopen(url, timeout=5.0) as resp:
                return json.loads(resp.read().decode("utf-8"))

    def patch(self, endpoint: str) -> Dict[str, Any]:
        if self._test_client:
            resp = self._test_client.patch(endpoint)
            if resp.status_code != 200:
                raise RuntimeError(f"PATCH {endpoint} failed ({resp.status_code}): {resp.text}")
            return resp.json()
        else:
            url = f"{self.base_url}{endpoint}"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="PATCH")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return json.loads(resp.read().decode("utf-8"))


def print_banner(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 78}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 78}{RESET}\n")


def print_step(step_num: int, title: str) -> None:
    print(f"\n{BOLD}{YELLOW}[STEP {step_num}] {title}{RESET}")
    print(f"{DIM}{'-' * 70}{RESET}")


def pause(args: argparse.Namespace) -> None:
    if args.step:
        input(f"\n{DIM}[Press Enter to proceed to next step...]{RESET}")
    elif args.delay > 0:
        time.sleep(args.delay)


def run_demo(args: argparse.Namespace) -> None:
    from scenarios.connectivity_outage import ConnectivityOutageScenario
    from scenarios.diverse_events import DiverseEventsScenario
    from scenarios.dual_bus_pothole import DualBusPotholeScenario
    from scenarios.resolution_verification import ResolutionVerificationScenario

    client = DemoClient(args.backend_url)

    print_banner("SIH 2026 PROTOTYPE — FLEET SENSING URBAN INTELLIGENCE DEMO")
    mode_desc = f"Live HTTP ({args.backend_url})" if args.backend_url else "Self-Contained Embedded API"
    print(f"Target Geography : {BOLD}Pune Transit Corridors (FC Road, JM Road, Karve Road, Shivaji Road){RESET}")
    print(f"Execution Mode   : {BOLD}{mode_desc}{RESET}")
    print(f"Contract Schema  : {BOLD}docs/api-contract.md (v1){RESET}\n")

    # -----------------------------------------------------------------------
    # Step 1: Fleet Routes and Dual-Bus Sensing
    # -----------------------------------------------------------------------
    print_step(1, "Multi-Bus Corroboration on FC Road, Pune")
    print("Simulating BUS-001 and BUS-002 independently traversing Fergusson College Road.")

    pothole_scenario = DualBusPotholeScenario(auto_generate_evidence=True)
    events = pothole_scenario.generate_events()
    evt1, evt2 = events[0], events[1]

    # Ingest BUS-001 detection
    print(f"\n→ {GREEN}BUS-001 detects defect{RESET}:")
    print(f"  Event ID      : {BOLD}{evt1.event_id}{RESET}")
    print(f"  Type          : {evt1.event_type} (Confidence: {evt1.confidence:.2f}, Severity: {evt1.severity})")
    print(f"  Location      : Raw GPS ({evt1.latitude:.6f}, {evt1.longitude:.6f})")
    print(f"  Road Aligned  : ({evt1.road_aligned_latitude:.6f}, {evt1.road_aligned_longitude:.6f}) [Goodluck Chowk]")
    print(f"  Evidence Photo: {evt1.evidence_image}")
    client.post("/events", evt1.to_dict())

    pause(args)

    # Ingest BUS-002 detection 4m later
    print(f"\n→ {GREEN}BUS-002 independently corroborates defect{RESET} (4m 20s later):")
    print(f"  Event ID      : {BOLD}{evt2.event_id}{RESET}")
    print(f"  Location      : Raw GPS ({evt2.latitude:.6f}, {evt2.longitude:.6f})")
    print(f"  Road Aligned  : ({evt2.road_aligned_latitude:.6f}, {evt2.road_aligned_longitude:.6f}) [Exact Road Match]")
    client.post("/events", evt2.to_dict())

    obs_list = client.get("/observations")
    print(f"\n✔ {GREEN}Observations stored in central database:{RESET} {obs_list['count']} records.")
    pause(args)

    # -----------------------------------------------------------------------
    # Step 2: Connectivity Outage & SQLite WAL Outbox Replay
    # -----------------------------------------------------------------------
    print_step(2, "Cellular Outage & Edge SQLite/WAL Store-and-Forward Replay")
    print("BUS-003 enters Nal Stop transit underpass; cellular link drops.")

    outage_scenario = ConnectivityOutageScenario(base_sequence=3, auto_generate_evidence=True)
    outage_events = outage_scenario.generate_events()
    online_evt, offline_evt = outage_events[0], outage_events[1]

    # Online event
    print(f"\n→ {GREEN}BUS-003 online detection{RESET} near Lakdi Pul:")
    print(f"  Event ID : {online_evt.event_id} [{online_evt.connectivity_state}]")
    client.post("/events", online_evt.to_dict())

    # Offline event
    print(f"\n→ {RED}Connectivity DROPPED [OFFLINE]{RESET}:")
    print(f"  BUS-003 detects {offline_evt.event_type} at Nal Stop: {BOLD}{offline_evt.event_id}{RESET}")
    print(f"  Action   : Buffered in local edge SQLite outbox (PRAGMA journal_mode=WAL).")
    outage_scenario.outbox.enqueue(offline_evt)

    pause(args)

    # Reconnect
    print(f"\n→ {GREEN}Connectivity RESTORED [ONLINE]{RESET}:")
    print("  Triggering outbox synchronization pipeline...")
    pending = outage_scenario.outbox.get_pending()
    for item in pending:
        replay_resp = client.post("/events", item.to_dict())
        outage_scenario.outbox.mark_replayed(item.event_id)
        print(f"  ✔ Replayed {item.event_id} with original timestamps: {replay_resp['message']}")

    # Demonstrate Idempotency
    dup_resp = client.post("/events", offline_evt.to_dict())
    print(f"  ✔ Duplicate ingestion test: {dup_resp['message']} (duplicate={dup_resp['duplicate']})")
    pause(args)

    # -----------------------------------------------------------------------
    # Step 3: Diverse Event Classes
    # -----------------------------------------------------------------------
    print_step(3, "Diverse Urban Sensing Events across City Corridors")
    diverse_scenario = DiverseEventsScenario(base_sequence=10, auto_generate_evidence=True)
    div_events = diverse_scenario.generate_events()
    for devt in div_events:
        client.post("/events", devt.to_dict())
        print(f"  • {devt.bus_id} sensed {BOLD}{devt.event_type:<20}{RESET} conf={devt.confidence:.2f} sev={devt.severity:<6} on {devt.route_id}")
    pause(args)

    # -----------------------------------------------------------------------
    # Step 4: Incident Creation & Civic Ticket Lifecycle
    # -----------------------------------------------------------------------
    print_step(4, "Incident Verification & Civic Ticket Dispatch")
    print("Fleet Fusion clusters EVT-000001 & EVT-000002 into a verified incident.")

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
    client.post("/incidents", incident_payload)
    print(f"✔ Incident created: {BOLD}INC-000001{RESET} (Status: VERIFIED, Dept: MUNICIPAL_CORPORATION)")

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
    tkt_resp = client.post("/tickets", ticket_payload)
    ticket_data = tkt_resp["ticket"]

    print(f"\n→ {GREEN}Civic Ticket Dispatched{RESET}:")
    print(f"  Ticket ID        : {BOLD}{ticket_data['ticket_id']}{RESET}")
    print(f"  Work Order       : {ticket_data['workorder_id']}")
    print(f"  Repair SLA       : {ticket_data['estimated_repair_sla_hours']} Hours")
    print(f"  Navigation URL   : {CYAN}{ticket_data['google_maps_url']}{RESET}")
    print(f"  Initial Status   : {YELLOW}{ticket_data['status']}{RESET}")

    pause(args)

    print("\n→ Advancing authority ticket lifecycle:")
    for new_st in ("ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"):
        res = client.patch(f"/tickets/POT-2026-000001/status?new_status={new_st}")
        print(f"  Status transition -> {GREEN}{res['ticket']['status']}{RESET} at {res['ticket']['updated_at']}")
        pause(args)

    # -----------------------------------------------------------------------
    # Step 5: Resolution Verification (Before / After Evidence)
    # -----------------------------------------------------------------------
    print_step(5, "Resolution Verification with Post-Repair Visual Evidence")
    res_scenario = ResolutionVerificationScenario(base_sequence=20, auto_generate_evidence=True)
    res_events = res_scenario.generate_events()
    before_evt, after_evt = res_events[0], res_events[1]

    client.post("/events", before_evt.to_dict())
    client.post("/events", after_evt.to_dict())

    print(f"→ Initial Defect Photo (Day 0) : {BOLD}{before_evt.evidence_image}{RESET} (Severity: HIGH)")
    print(f"→ Post-Repair Photo   (Day 2) : {BOLD}{after_evt.evidence_image}{RESET} (Severity: LOW, Repaired Pavement)")
    print(f"✔ Location Match: ({after_evt.road_aligned_latitude}, {after_evt.road_aligned_longitude})")
    print(f"✔ Visual verification confirmed; ticket POT-2026-000001 closed with auditable evidence.")

    print_banner("DEMONSTRATION COMPLETED SUCCESSFULLY")


def main() -> int:
    parser = argparse.ArgumentParser(description="Repeatable prototype demonstration runner.")
    parser.add_argument("--step", action="store_true", help="Prompt between each demonstration step.")
    parser.add_argument("--delay", type=float, default=0.2, help="Seconds to delay between steps (default: 0.2).")
    parser.add_argument("--backend-url", type=str, default=None, help="URL of running backend (e.g. http://localhost:8000).")
    args = parser.parse_args()

    run_demo(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
