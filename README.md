# Beyonders Urban Intelligence

AI-Powered Mobile Urban Intelligence Platform — SIH 2026 prototype.

The prototype uses buses as mobile sensing units to identify civic-road and safety events, attach evidence and road-aligned location data, combine observations from the fleet, and show prioritized incidents and their civic-ticket progress on a map.

## Prototype outcome

The first reliable vertical slice is:

```text
Data/Test/Demo Simulator → MQTT → FastAPI → PostgreSQL/PostGIS → GIS dashboard
```

Then connect the actual bus path and offline behavior:

```text
Camera/video → YOLO + ByteTrack → evidence image + GNSS/GPS/IMU → SQLite/WAL queue → MQTT → same backend flow
```

Multiple independent observations can be fused into one verified incident, prioritized, routed to a department, and tracked with a ticket such as `POT-2026-000001` until resolution is verified.

## Architecture

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
       incident/severity → department ticket → React/Leaflet GIS
                                      ↓
                    continued bus observations → resolution check
```

Read [architecture.md](docs/architecture.md) and [api-contract.md](docs/api-contract.md) before implementing a component.

## Repository map

| Area | Purpose now | Primary pair |
| --- | --- | --- |
| `ai/`, `edge/`, `bus-simulator/` | Future camera, YOLO, ByteTrack, GNSS/IMU, offline queue, and event work | Group 1 — Member 1 (AI/ML) and Member 2 (Edge/Bus Simulator) |
| `backend/`, `database/`, `fusion/` | API ingestion, PostGIS foundation, incident fusion, and resolution policy | Group 2 — Member 3 (Backend) and Member 4 (Database/Fusion) |
| `dashboard/`, `data-demo-simulator/`, `scripts/` | GIS UI, deterministic demo data, CI, and integration environment | Group 3 — Member 5 (GIS) and Member 6 (Integration/DevOps) |

This grouping establishes shared ownership; exact member assignments can be recorded in issues.

## Prototype stack

- Edge/AI: Python, OpenCV, YOLO, ByteTrack, and ONNX; TensorRT is optional later.
- Edge transport: MQTT/Mosquitto with SQLite buffering where connectivity is unavailable.
- Central platform: FastAPI, Pydantic, SQLAlchemy, PostgreSQL, and PostGIS.
- GIS: React, Vite, Leaflet, and OpenStreetMap.
- Development: Docker Compose, GitHub Actions, GitHub Issues, and pull requests.

## Start here

1. Read [prototype-scope.md](docs/prototype-scope.md), [architecture.md](docs/architecture.md), and [api-contract.md](docs/api-contract.md).
2. Copy `.env.example` to `.env` and fill in local values when services are introduced. Do not commit `.env`.
3. Create a small GitHub Issue with acceptance criteria.
4. Branch from `develop` using `feature/…`, `fix/…`, `docs/…`, or `test/…`.
5. Open a pull request to `develop`; CI and a teammate review it.

The intended branch flow is `feature/* → develop → main`. `main` must remain demo-ready.

## What is intentionally not implemented

There is no model, inference pipeline, backend API, database schema, dashboard application, or production deployment in this initial commit. The architecture and contracts describe the intended prototype; implementation thresholds and service APIs must be approved through documented issues and pull requests.

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
