# Fleet Sensing Urban Intel — Real-Time GIS Operations Dashboard

Interactive GIS and civic operations dashboard for the SIH 2026 Fleet Sensing Urban Intelligence prototype in Pune, Maharashtra.

Owned by **Member 5 (GIS Dashboard)** per `docs/team-tasks/member-5-gis-dashboard.md` and `AGENTS.md`.

---

## Key Capabilities

1. **Real Leaflet GIS Engine**:
   - Genuine interactive map powered by **Leaflet.js** and **OpenStreetMap** standard tiles (`EPSG:4326 / WGS84`).
   - Centered on Pune municipal transit corridors (`[18.5204, 73.8436]`).
   - Dynamic GeoJSON layers:
     - **Pune Transit Corridors**: Polyline representation of FC Road (`ROUTE-PUNE-FC`), JM Road (`ROUTE-PUNE-JM`), Karve Road (`ROUTE-PUNE-KARVE`), and Shivaji Road (`ROUTE-PUNE-SHIVAJI`) with interactive waypoint tooltips.
     - **Sensed Defect Markers**: Color-coded markers for `POTHOLE` (red), `GARBAGE` (green), `TRAFFIC_OBSTRUCTION` (amber), and `PEDESTRIAN_RISK` (purple) with animated pulsing severity halos for `HIGH` severity.
     - **Live Bus Fleet Locations**: Dynamic bus pins showing current positions of `BUS-001` through `BUS-006` with online/offline status.
   - Interactive GIS layer control toolbar to toggle layers on and off.

2. **100% Dynamic Live Backend Connectivity (Zero Mock Data)**:
   - All static mock/dummy data arrays have been purged.
   - Directly fetches working operational data from FastAPI backend REST APIs:
     - `GET /api/v1/stats`: Real-time KPI counts (incidents, verified defects, open tickets, online fleet).
     - `GET /api/v1/incidents`: Corroborated defect incidents.
     - `GET /api/v1/incidents/geojson`: RFC 7946 GeoJSON FeatureCollection.
     - `GET /api/v1/tickets`: Civic work orders.
     - `GET /api/v1/fleet`: Active bus telemetry, battery, and edge AI health.
     - `GET /api/v1/routes/geojson`: Road alignment vectors.

3. **Real-Time Polling & Ingestion Sync**:
   - 4-second live background polling engine.
   - Any new event published by the **Actual Bus Simulator** or **Data/Demo Simulator** instantly updates the map, defect table, and KPI cards.
   - Visual "API Live" pulsing indicator.

4. **Interactive Civic Ticket Lifecycle**:
   - Complete Kanban board (`REPORTED` → `ACKNOWLEDGED` → `IN_PROGRESS` → `RESOLVED`).
   - Advancing status directly executes `PATCH /api/v1/tickets/{id}/status?new_status=...` against the backend.
   - Un-ticketed incidents can be dispatched directly with "⚡ Raise Civic Ticket" calling `POST /api/v1/tickets`.
   - Before/after visual evidence verification inspection.

5. **Direct Navigation**:
   - One-click Google Maps directions URL (`https://www.google.com/maps?q={lat},{lng}`) generated from road-aligned coordinates.

---

## How to Run

### Option A: Complete Prototype Launcher (Recommended)
Run the all-in-one launcher script from the repository root:
```bash
python3 scripts/run_prototype.py
```
This boots the backend, seeds Pune corridor data, and opens `http://localhost:8000/dashboard` in your browser.

### Option B: Run Backend Directly
```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 8000
```
Navigate to:
```text
http://localhost:8000/dashboard
```

### Option C: Standalone File View (Offline Resilience)
You can also open `dashboard/index.html` directly in any browser:
```bash
open dashboard/index.html
# or with python's local server
python3 -m http.server 3000 --directory dashboard
```

---

## How to Test

Run the automated dashboard integration test suite:
```bash
pytest tests/test_dashboard_integration.py -v
```
This tests:
- HTML file structure and Leaflet GIS integration.
- FastAPI delivery of `GET /dashboard`.
- Contract adherence of GeoJSON layers (`/incidents/geojson`, `/routes/geojson`).
- Fleet telemetry and platform stats API endpoints.
- Full ticket status transition lifecycle synchronization.
