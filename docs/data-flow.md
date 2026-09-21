# Data Flow

1. An input path emits a contract-valid event: the Actual Bus Simulator after detection/tracking/event rules, or the Data/Test/Demo Simulator from a scripted route.
2. The event includes an evidence-image reference, original GNSS/GPS coordinates, UTC timestamp, confidence, and road-aligned coordinates when available.
3. When disconnected, the edge writes the event to a SQLite WAL queue. When connected, it publishes through MQTT on `beyonders/events/v1`; replay uses the original `event_id`.
4. FastAPI validates the v1 contract idempotently and persists one immutable event/observation in PostgreSQL/PostGIS.
5. Location processing uses map matching (HMM-compatible, with Valhalla/OSRM as planned routing/matching services) while retaining original coordinates.
6. Fleet fusion uses compatible event type, spatial-temporal proximity, independent buses, confidence, evidence, and persistence. ST-DBSCAN proposes groups; Bayesian evidence update supports explainable confidence.
7. Fusion creates/updates an incident, derives severity, routes it to a department, and creates a ticket only when the incident is verified.
8. Continued bus observations can generate a resolution candidate; the authority lifecycle records the decision.
9. The React/Leaflet dashboard displays the resulting state without rewriting source observations.

Retry policy, exact SQLite schema, deduplication behavior, fusion thresholds, severity formula, and map-matching deployment are implementation decisions. They must be documented and tested before adoption; this document records the required behavior, not hidden defaults.
