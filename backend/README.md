# Fleet Sensing Urban Intelligence — Backend

FastAPI backend service responsible for contract-valid event ingestion, observation persistence, incident management, civic ticket lifecycle handling, and GIS GeoJSON layers.

---

## Requirements

- Python 3.10+ (Recommended: Python 3.12)
- Dependencies listed in `requirements.txt`:
  - `fastapi`
  - `uvicorn[standard]`
  - `pydantic`
  - `pytest`
  - `httpx`
  - `sqlalchemy`
  - `alembic`
  - `shapely`
  - `geoalchemy2`

---

## Running in a Virtual Environment

1. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Launch the FastAPI application**:
   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Access Endpoints & UI**:
   - **Real GIS Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
   - **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc API Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## API Endpoints

All endpoints are available at both root and versioned `/api/v1` prefixes:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` / `/` | Service health, contract version, and dashboard URL |
| `GET` | `/dashboard` | Serves the single-page Leaflet GIS operations dashboard |
| `POST` | `/events` | Idempotent event ingestion (creates normalized Observation) |
| `GET` | `/events` | List all ingested events |
| `GET` | `/events/{event_id}` | Retrieve event by ID |
| `GET` | `/observations` | List all persisted observations |
| `GET` | `/observations/{observation_id}` | Retrieve observation by ID |
| `POST` | `/incidents` | Register or update verified/candidate incident |
| `GET` | `/incidents` | List all incidents |
| `GET` | `/incidents/{incident_id}` | Retrieve incident by ID |
| `GET` | `/incidents/geojson` | **GIS**: RFC 7946 GeoJSON FeatureCollection of defect incidents |
| `GET` | `/routes/geojson` | **GIS**: RFC 7946 GeoJSON FeatureCollection of Pune transit corridors |
| `GET` | `/fleet` | List active fleet buses with routes, battery, and telemetry |
| `GET` | `/fleet/{bus_id}` | Retrieve bus telemetry and edge AI health |
| `GET` | `/stats` | Aggregate platform analytics for GIS dashboard KPI cards |
| `POST` | `/demo/seed` | Seed authentic Pune transit demonstration dataset into memory |
| `POST` | `/tickets` | Create civic ticket (`POT-YYYY-XXXXXX`) |
| `GET` | `/tickets` | List all tickets |
| `GET` | `/tickets/{ticket_id}` | Retrieve ticket by ID |
| `PATCH`| `/tickets/{ticket_id}/status` | Update ticket lifecycle status (`REPORTED` → `ACKNOWLEDGED` → `IN_PROGRESS` → `RESOLVED`) |
| `GET` | `/tickets/{ticket_id}/map` | Get Google Maps navigation link |

---

## Running Tests

Run the backend test suite using pytest inside the virtual environment:
```bash
pytest backend/tests -v
```
