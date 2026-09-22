# Dashboard

A minimal GIS dashboard is served from the backend at http://localhost:8000/dashboard.

It is intentionally lightweight and prototype-friendly: it fetches the live incidents, tickets, and observations from the FastAPI API and renders a simple Leaflet-based map for end-to-end demo use.

## Run it

1. Start the API:
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
2. Open:
   http://localhost:8000/dashboard
3. Seed or ingest events via the simulator or API to populate the map.
