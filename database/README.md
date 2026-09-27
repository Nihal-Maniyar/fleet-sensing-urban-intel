# Database Layer (PostgreSQL 16 + PostGIS 3.4)

Provides the spatial, relational, and event-sourcing foundation for the **Beyonders Urban Intelligence** platform. Owned by **Group 2 (Member 4 — Database & Fleet Fusion)** in close coordination with **Member 3 (Backend APIs)**.

---

## 1. Schema & Core Entities

The database implements 7 core tables adhering to `docs/database.md` and `docs/api-contract.md`:

| Table | Primary Key | Description | Key Constraints & Indexes |
|---|---|---|---|
| **`buses`** | `bus_id` (`BUS-001`) | Fleet bus registry and route telemetry status. | Unique ID format `BUS-XXX`, boolean `is_active`. |
| **`events`** | `event_id` (`EVT-000001`) | Raw incoming edge/simulator detections. | Foreign key to `buses.bus_id`, CHECK `connectivity_state IN ('ONLINE', 'OFFLINE')`. Idempotent ingestion. |
| **`observations`** | `observation_id` (`OBS-000001`) | Normalized observation facts with dual coordinates. | Unique `event_id`, GiST spatial indexes on `geom_raw` and `geom_road_aligned` (SRID 4326). |
| **`incidents`** | `incident_id` (`INC-000001`) | Fused incidents across fleet observations. | Centroid `geom` with GiST spatial index. CHECK status `(CANDIDATE, VERIFIED, REJECTED, RESOLUTION_CANDIDATE, RESOLVED)`. |
| **`incident_observations`** | Composite `(incident_id, observation_id)` | Audit junction preserving the complete evidence trail. | Foreign keys with `ON DELETE RESTRICT` for observation evidence preservation. |
| **`tickets`** | `ticket_id` (`POT-YYYY-XXXXXX`) | Civic authority tickets created for verified incidents. | Unique `incident_id`, check status `(REPORTED, ACKNOWLEDGED, IN_PROGRESS, RESOLVED)`. |
| **`ticket_status_history`** | `id` (autoincrement) | Append-only audit trail of civic status transitions. | Foreign key to `tickets.ticket_id`, indexed on `(ticket_id, changed_at)`. |

---

## 2. Invariants & Rules

1. **Dual Coordinate Preservation**: Original GNSS/GPS coordinates (`latitude`, `longitude`) and map-matched coordinates (`road_aligned_latitude`, `road_aligned_longitude`) are stored separately. Raw coordinates are **never** overwritten.
2. **Idempotent Ingestion**: Network reconnection replays use the same `event_id`. Duplicate event ingestion is prevented at the database level and through `insert_event_idempotent`.
3. **Evidence Preservation**: Fleet fusion must never delete observations or discard evidence images.
4. **Spatial Indexing**: PostGIS geometry columns use SRID 4326 with GiST spatial indexes.

---

## 3. Quick Start & Migrations

### Running Migrations

Ensure PostgreSQL/PostGIS is running (e.g. via `docker compose up -d postgis`). Then run:

```bash
# Apply migrations to head
alembic upgrade head

# Rollback migration if needed
alembic downgrade -1
```

### Seeding Pune Demo Data

To populate realistic Pune demonstration buses, observations, candidate/verified incidents, and tickets:

```bash
python -m database.seed
# or
python scripts/seed_demo_data.py
```

---

## 4. Usage in Backend Services

```python
from database import (
    get_db,
    insert_event_idempotent,
    create_observation,
    find_incidents_near,
    query_incidents_in_bbox,
)

# In FastAPI dependency:
@app.post("/events")
def ingest_event(payload: dict, db: Session = Depends(get_db)):
    event, created = insert_event_idempotent(db, payload)
    return {"event_id": event.event_id, "created": created}
```

---

## 5. Spatial Utilities (`database/spatial.py`)

- `find_incidents_near(session, lat, lon, radius_meters=15.0)`: Spatial proximity query (default 15m). Uses PostGIS `ST_DWithin` on geography in PostgreSQL.
- `find_observations_near(session, lat, lon, radius_meters=15.0, use_road_aligned=False)`: Finds nearby observations.
- `query_incidents_in_bbox(session, min_lat, min_lon, max_lat, max_lon, status=None)`: Viewport bounding box query utilizing GiST index.
- `haversine_distance_meters(lat1, lon1, lat2, lon2)`: Spherical great-circle distance calculation in meters.
