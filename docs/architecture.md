# Architecture

## Agreed system flow

```text
Actual Bus Simulator                         Data/Test/Demo Simulator
camera + GNSS/NavIC + IMU                    scripted/replay route events
        ↓                                             ↓
YOLO → ByteTrack → event + evidence          contract-valid event + evidence
        ↓                                             ↓
SQLite WAL queue when offline ───── MQTT/store-and-forward ───────┘
                                      ↓
                                  FastAPI
                                      ↓
                           PostgreSQL + PostGIS
                                      ↓
        HMM map matching (Valhalla/OSRM where available)
                                      ↓
             ST-DBSCAN + Bayesian evidence update
                                      ↓
          severity → incident → authority ticket → GIS dashboard
                                      ↓
                         later observations verify resolution
```

## Responsibilities

- Edge produces an immutable event payload and an evidence-image reference. It performs lightweight inference, tracking, temporal event rules, and local buffering; it does not decide whether a fleet incident is verified.
- FastAPI validates and persists events/observations and exposes data to fusion and the dashboard.
- SQLite/WAL is the edge store-and-forward buffer for connectivity loss. MQTT is the preferred event transport when connectivity is available.
- GNSS/NavIC provides location; IMU helps account for camera motion. Map matching turns noisy positions into road-aligned positions without discarding the original coordinates.
- PostGIS stores geographic data and supports proximity/road-segment queries; policy remains explicit and testable.
- Fleet fusion combines compatible observations with spatial-temporal clustering (ST-DBSCAN) and an explainable Bayesian evidence update. It preserves every source observation.
- The dashboard shows buses, event evidence, road condition/hotspots, incidents, severity, department tickets, and resolution state.

## Two simulators

The **Actual Bus Simulator** represents the camera/video and edge path. The **Data/Test/Demo Simulator** publishes deterministic contract-valid events so the full platform can be demonstrated before CV is ready. Details are in [simulators.md](simulators.md).

## Boundaries

MQTT is the transport from simulators/edge to ingestion; SQLite/WAL is the offline boundary. The API contract, not an internal implementation detail, is the boundary between groups. Use versioned MQTT topics and documented payloads.
