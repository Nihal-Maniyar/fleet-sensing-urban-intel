# Prototype Scope

## In scope

- A complete pothole story first. The limited initial candidate event types are `POTHOLE`, `GARBAGE`, `TRAFFIC_OBSTRUCTION`, and `PEDESTRIAN_RISK`; do not expand this set without team agreement. The exact classes implemented remain an AI decision, but pothole is required for the primary demo.
- Two input paths: actual-bus video/camera simulation and deterministic data/test/demo events.
- YOLO detection and ByteTrack tracking as the intended edge-CV architecture.
- Evidence image references, UTC timestamp, bus ID, confidence, GNSS/GPS coordinates, optional IMU context, and road-aligned coordinates.
- MQTT transport with SQLite/WAL store-and-forward for network outages.
- FastAPI, PostgreSQL/PostGIS, road-aligned location handling/map matching where useful, simple configurable fleet fusion, and a React/Leaflet map.
- Explainable severity/prioritization, authority routing, incident verification, and civic tickets using `POT-YYYY-XXXXXX`.
- Continued observations that can provide resolution evidence after repair.
- A work-order handoff after ticket assignment, represented as a lifecycle step rather than a municipal-system integration.

## Out of scope for the first vertical slice

- Production deployment, authentication/roles, predictive maintenance, automated municipal integrations, and full city-scale operations.
- Full ANPR/hit-and-run evidence workflows, complete origin-destination analytics, and every possible road-defect class.
- Production-grade model serving, hardware certification, and guaranteed map-matching accuracy.

## Delivery sequence

1. **Foundation:** contracts, Git workflow, CI skeleton, local service scaffold.
2. **Vertical slice:** Demo Simulator → MQTT → FastAPI → PostGIS → map with a road-positioned incident.
3. **Edge input:** Actual Bus Simulator → YOLO + ByteTrack → evidence event into the same ingestion path.
4. **Resilience:** disconnect/reconnect → SQLite/WAL queue → MQTT synchronization without duplicate events.
5. **Fleet value:** multiple buses → road alignment → configurable spatial-temporal fusion → verified incident → severity → ticket.
6. **Resolution:** later bus observations provide evidence that the issue is resolved; the authority lifecycle remains auditable.
7. **Demo hardening:** repeatable scenarios, seeded routes/events, and a clear operator view.

## Geographic demonstration rule

The main GIS scenario must use realistic road-aligned coordinates and routes. Pune roads are the default demonstration geography. Random points may be used only for isolated tests, never as the principal judge-facing map story.
