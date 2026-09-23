# Fleet Sensing Urban Intel — Real-Time GIS Operations Dashboard

Interactive GIS and civic operations dashboard for the SIH 2026 Fleet Sensing Urban Intelligence prototype in Pune, Maharashtra.

Owned by **Member 5 (GIS Dashboard)** per `docs/team-tasks/member-5-gis-dashboard.md`, `frontend-design/SKILL.md`, and `AGENTS.md`.

---

## Key Capabilities

1. **Strict Road Alignment & Map Matching**:
   - **Guaranteed Road-Centered Locations**: Sensed defect pins and bus locations are anchored strictly over the Pune road corridor polylines (`EPSG:4326 / WGS84`).
   - **Algorithmic Snapping (`snapToRoadCorridor`)**: Computes the nearest road corridor segment and snaps coordinates precisely to the road centerline.
   - **GNSS Satellite Drift Vectors**: When raw satellite GNSS coordinates differ from the snapped road location (e.g. 8.4m satellite drift), a dashed vector line connects the raw satellite fix to the road marker, visually proving edge-to-road alignment and map matching.
   - **Pune Transit Corridors**: Polyline representation of FC Road (`ROUTE-PUNE-FC`), JM Road (`ROUTE-PUNE-JM`), Karve Road (`ROUTE-PUNE-KARVE`), and Shivaji Central (`ROUTE-PUNE-SHIVAJI`) with interactive waypoint tooltips.

2. **Real-Time Bi-Directional Streaming (WebSockets + Polling Fallback)**:
   - **WebSocket Endpoint (`/ws` and `/api/v1/ws`)**: Connected clients receive instant push notifications (<50ms latency) on:
     - `EVENT_INGESTED`: New event from Actual Bus Simulator or Demo Simulator.
     - `INCIDENT_CREATED` / `INCIDENT_UPDATED`: Spatial-temporal fleet fusion updates.
     - `TICKET_CREATED` / `TICKET_STATUS_UPDATED`: Civic lifecycle updates.
     - `FLEET_UPDATED`: Real-time bus coordinates, heading, and telemetry.
     - `STATS_UPDATED`: KPI counts.
   - **Resilient Polling**: 3-second background polling fallback ensures 100% data consistency even across restrictive network proxies.

3. **In-Dashboard Interactive Simulation Triggers**:
   - 1-click execution of key vertical slice demonstration scenarios directly from the dashboard:
     - `▶ Dual-Bus Corroboration (FC Road)`: Simulates BUS-001 and BUS-002 corroborating a pothole at Goodluck Chowk, fusing into `INC-000001`, and generating `POT-2026-000001`.
     - `▶ Offline WAL Replay (Nal Stop Tunnel)`: Simulates offline event buffering in SQLite/WAL and idempotent replay upon reconnection.
     - `▶ Post-Repair Resolution`: Simulates smooth asphalt detection and advances the civic ticket to `RESOLVED`.
     - `⚡ Reset & Seed Pune Corridors`: Re-seeds the baseline authentic Pune dataset.

4. **Civic Ticket Lifecycle Stepper & Actions**:
   - Complete 4-stage lifecycle: `REPORTED` → `ACKNOWLEDGED` → `IN_PROGRESS` → `RESOLVED`.
   - Advancing status directly executes `PATCH /api/v1/tickets/{id}/status?new_status=...` against the backend, broadcasting updates to all connected dashboards in real time.
   - Before/after visual evidence verification inspection.

5. **Edge AI Defect Evidence & Bounding Boxes**:
   - Actual defect evidence photos served from `/runtime/evidence/...` with YOLOv8 detection tags and ByteTrack corroboration.
   - Direct Google Maps navigation link (`https://www.google.com/maps/dir/?api=1&destination=lat,lng`).

---

## How to Run

### Option A: Complete Prototype Launcher (Recommended)
Run the all-in-one launcher script from the repository root:
```bash
./.venv/bin/python scripts/run_prototype.py
```
This boots FastAPI, seeds Pune corridor data, and opens `http://localhost:8000/dashboard` in your browser.

### Option B: Run Backend Directly
```bash
./.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```
Navigate to:
```text
http://localhost:8000/dashboard
```

---

## How to Test

Run the automated dashboard integration test suite:
```bash
./.venv/bin/pytest tests/test_dashboard_integration.py -v
```

All 12 tests verify:
- HTML file structure and Leaflet GIS integration.
- FastAPI delivery of `GET /dashboard`.
- Contract adherence of GeoJSON layers (`/incidents/geojson`, `/routes/geojson`).
- Fleet telemetry and platform stats API endpoints.
- Full ticket status transition lifecycle synchronization.
- Real-time WebSocket connection and message streaming.
- Simulator interactive trigger execution.
- Static evidence photo serving.
- Authentic Pune road corridor snapping and coordinate validation.
