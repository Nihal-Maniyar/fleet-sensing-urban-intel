# Beyonders Urban Intelligence

AI-Powered Mobile Urban Intelligence Platform — SIH 2026 prototype.

The prototype uses city transit buses as mobile sensing units to identify civic-road and safety defects, attach evidence and road-aligned location data, combine observations across the fleet, and display prioritized incidents and civic-ticket progress on a real-time GIS map.

---

## Prototype Data Flow

```text
Actual Bus Simulator                         Data/Test/Demo Simulator
Camera/video + GNSS/NavIC + IMU              deterministic route/event replay
        ↓                                             ↓
YOLO + ByteTrack → event/evidence       contract-valid event/evidence
        ↓                                             ↓
SQLite/WAL queue (offline) ─────── MQTT/store-and-forward ───────┘
                                      ↓
                              FastAPI ingestion
                                      ↓
                         PostgreSQL + PostGIS storage
                                      ↓
       road alignment + configurable spatial-temporal fleet fusion
                                      ↓
       incident/severity → department ticket → Real-time Leaflet GIS Dashboard
                                      ↓
                    continued bus observations → resolution check
```

---

## Quickstart: Run the Complete Prototype

Run the unified prototype launcher with a single command:

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Launch prototype (boots backend, seeds Pune corridor data, opens GIS dashboard)
python3 scripts/run_prototype.py
```

- **Real GIS Operations Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## Running & Testing Individual Components

### 1. Central Backend & GIS Engine (`backend/`)
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- Test backend: `pytest backend/tests -v`

### 2. Real GIS Operations Dashboard (`dashboard/`)
- When backend is running, open [http://localhost:8000/dashboard](http://localhost:8000/dashboard).
- Leaflet.js real OpenStreetMap tiles, Pune transit corridors (FC Road, JM Road, Karve Road, Shivaji Road), defect pins with pulsing alert rings, live bus fleet positions, and direct ticket lifecycle management.
- Test dashboard integration: `pytest tests/test_dashboard_integration.py -v`

### 3. Data/Test/Demo Simulator (`data-demo-simulator/`)
Deterministic, contract-valid synthetic Pune transit events:
```bash
# Run dual-bus pothole corroboration scenario
python3 data-demo-simulator/main.py --scenario dual_bus_pothole

# Stream master demo directly into backend over HTTP
python3 data-demo-simulator/main.py --scenario master_demo --mode http --http-url http://localhost:8000/api/v1/events --delay 0.5
```
- Test data simulator: `python3 -m unittest discover -s data-demo-simulator/tests -q`

### 4. Actual Bus Simulator (`bus-simulator/`)
Edge AI computer vision sensing pipeline (YOLO + ByteTrack + 6-DOF IMU + SQLite/WAL):
```bash
# Launch Bus 1 on FC Road (Web UI on port 8001):
python3 bus-simulator/main.py --bus-id BUS-001 --route ROUTE-PUNE-FC --port 8001

# Launch Bus 2 simultaneously on JM Road (Web UI on port 8002):
python3 bus-simulator/main.py --bus-id BUS-002 --route ROUTE-PUNE-JM --port 8002
```
- Test bus simulator: `python3 -m unittest discover -s bus-simulator/tests -q`

### 5. Automated 5-Step Demo Runner (`scripts/run_demo.py`)
```bash
python3 scripts/run_demo.py --delay 0.5
```

---

## Complete Test Suite Execution

Run all 59+ unit and integration tests across all repository components:
```bash
pytest -v
```

---

## Repository Map

| Area | Component | Primary Owner |
|---|---|---|
| `bus-simulator/` | YOLO detection, ByteTrack tracking, GNSS/IMU coupling, SQLite/WAL queue | Group 1 — Member 1 (AI/ML) and Member 2 (Edge/Bus Simulator) |
| `backend/`, `database/` | FastAPI endpoints, PostGIS spatial models, Alembic migrations, ticket lifecycle | Group 2 — Member 3 (Backend) and Member 4 (Database/Fusion) |
| `dashboard/`, `data-demo-simulator/`, `scripts/` | Real Leaflet GIS UI, demo simulator, CI/CD, and prototype launcher | Group 3 — Member 5 (GIS Dashboard) and Member 6 (DevOps/Integration) |

---

## Documentation

- [Architecture](docs/architecture.md)
- [Prototype scope and milestones](docs/prototype-scope.md)
- [API and data contracts](docs/api-contract.md)
- [Data flow](docs/data-flow.md)
- [Database plan](docs/database.md)
- [AI and edge plan](docs/ai-pipeline.md)
- [Fleet fusion rules](docs/fleet-fusion.md)
- [Simulator definitions](docs/simulators.md)
- [Ticket lifecycle](docs/ticket-lifecycle.md)
- [Development workflow](docs/development.md)
- [Demo plan](docs/demo.md)
- [Team task briefs](docs/team-tasks/README.md)
