# Fleet Sensing Urban Intel — GIS Dashboard

Interactive GIS and civic operations dashboard for the SIH 2026 Fleet Sensing Urban Intelligence prototype in Pune.

Owned by **Member 5 (GIS Dashboard)** per `docs/team-tasks/member-5-gis-dashboard.md` and `AGENTS.md`.

## Features

- **Interactive Pune Transit Map**: Illustrative road-aligned SVG map projecting Pune transit corridors (FC Road, JM Road, MG Road, Karve Road, Wakad, Kothrud, Hadapsar, etc.).
- **Incident Management**:
  - Detailed drawer showing detection type, AI confidence, severity, detected coordinates, and detection by multiple independent buses.
  - Generative visual evidence display (bounding box annotation, class HUD).
  - One-click direct Google Maps navigation link.
- **Authority Ticket Lifecycle**:
  - Kanban board and lifecycle stepper (`REPORTED` → `ACKNOWLEDGED` → `IN_PROGRESS` → `RESOLVED`).
  - Auditable before-and-after visual resolution verification.
  - Live backend synchronization via `PATCH /api/v1/tickets/{id}/status`.
- **Fleet Sensing & Edge AI Health**:
  - Bus status indicators (`BUS-001` through `BUS-006`), route allocations, battery, uptime, and last event.
- **Fleet Fusion Queue**:
  - Unfused observation clustering view (`FUSION_DISTANCE_METERS <= 40m`, `FUSION_TIME_WINDOW_SECONDS <= 600s`).
- **Data Source Toggle**:
  - Switchable between **Data/Demo Simulator** and **Actual Bus Simulator** without UI redesign.
- **Dark / Light Mode**:
  - Built-in theme switcher with client-side preference persistence.

## Contract Compliance

Strictly follows `docs/api-contract.md`:
- **Identifiers**: `BUS-001`, `EVT-000001`, `OBS-000001`, `INC-000001`, `POT-YYYY-XXXXXX`.
- **Statuses**: `REPORTED`, `ACKNOWLEDGED`, `IN_PROGRESS`, `RESOLVED`.
- **Event Types**: `POTHOLE`, `GARBAGE`, `TRAFFIC_OBSTRUCTION`, `PEDESTRIAN_RISK`.
- **Coordinates**: Road-aligned and raw GPS in Pune bounding box.

## How to Run

### 1. Embedded with FastAPI Backend (Recommended)
When the FastAPI backend is running:
```bash
uvicorn backend.app.main:app --reload --port 8000
```
Navigate to:
```text
http://localhost:8000/dashboard
```

### 2. Standalone in Any Modern Browser
Open `dashboard/index.html` directly:
```bash
open dashboard/index.html
# or with python's built-in http server
python3 -m http.server 3000 --directory dashboard
```
