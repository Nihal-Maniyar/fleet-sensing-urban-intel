# Fleet Sensing Urban Intelligence — Backend

FastAPI backend service responsible for contract-valid event ingestion, observation persistence, incident management, and civic ticket lifecycle handling.

## Requirements

- Python 3.10+ (Recommended: Python 3.12)
- Dependencies listed in `requirements.txt`:
  - `fastapi`
  - `uvicorn[standard]`
  - `pydantic`
  - `pytest`
  - `httpx`

## Running in a Virtual Environment

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Launch the FastAPI application:
   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Or from within the `backend` directory:
   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. Interactive API Documentation:
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## API Endpoints

All endpoints are available at both root and versioned `/api/v1` prefixes:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` / `/` | Service health and contract version |
| `POST` | `/events` | Idempotent event ingestion (creates normalized Observation) |
| `GET` | `/events` | List all ingested events |
| `GET` | `/events/{event_id}` | Retrieve event by ID |
| `GET` | `/observations` | List all persisted observations |
| `GET` | `/observations/{observation_id}` | Retrieve observation by ID |
| `POST` | `/incidents` | Register or update verified/candidate incident |
| `GET` | `/incidents` | List all incidents |
| `GET` | `/incidents/{incident_id}` | Retrieve incident by ID |
| `POST` | `/tickets` | Create civic ticket (`POT-YYYY-XXXXXX`) |
| `GET` | `/tickets` | List all tickets |
| `GET` | `/tickets/{ticket_id}` | Retrieve ticket by ID |
| `PATCH`| `/tickets/{ticket_id}/status` | Update ticket lifecycle status |
| `GET` | `/tickets/{ticket_id}/map` | Get Google Maps navigation link |

## Running Tests

Run the test suite using pytest inside the virtual environment:
```bash
pytest backend/tests -v
```
