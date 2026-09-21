# Data Flow

1. An input path emits a contract-valid event: the Actual Bus Simulator after detection/tracking/event rules, or the Data/Test/Demo Simulator from a scripted route.
2. The event includes an evidence-image reference, original GNSS/GPS coordinates, UTC timestamp, confidence, and road-aligned coordinates when available.
3. When disconnected, the edge writes the event to a SQLite WAL queue. When connected, it publishes through MQTT on `beyonders/events/v1`; replay uses the original `event_id`.
4. FastAPI validates the v1 contract idempotently and persists one immutable event/observation in PostgreSQL/PostGIS.
5. Location processing road-aligns/map-matches positions where useful while retaining original coordinates.
6. Fleet fusion uses compatible event type, configurable spatial-temporal proximity, independent buses, confidence, evidence, and persistence. It is intentionally simple and explainable for the prototype.
7. Fusion creates/updates an incident, derives severity, routes it to a department, and creates a ticket only when the incident is verified. The ticket begins as `REPORTED`, contains a Google Maps link built from stored coordinates, and may receive a work-order handoff after acknowledgement.
8. Continued bus observations can generate a resolution candidate; the authority lifecycle records the decision.
9. The React/Leaflet dashboard displays the resulting state without rewriting source observations.

Retry policy, exact SQLite schema, deduplication behavior, fusion thresholds, severity formula, and map-matching deployment are implementation decisions. They must be documented and tested before adoption; this document records the required behavior, not hidden defaults.
