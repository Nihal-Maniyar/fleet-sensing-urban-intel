# API and Event Contract (v1)

This document locks shared names for the first prototype. Do not substitute local variants such as `lat`, `gps_lat`, or `latitude_value`.

## Naming rules

- IDs are strings: `bus_id`, `event_id`, `observation_id`, `incident_id`, `ticket_id`.
- Timestamps use ISO 8601 UTC, for example `2026-09-20T10:30:00Z`.
- Coordinates use WGS84 decimal degrees: `latitude`, `longitude`.
- `confidence` is a number from `0.0` through `1.0`; severity is a separate derived field.
- `evidence_image` is a storage URI/path, not embedded image bytes.
- `event_type` values for the prototype are `POTHOLE`, `ROAD_DAMAGE`, `GARBAGE`, `WATERLOGGING`, `ILLEGAL_PARKING`, `VEHICLE`, and `PERSON`. Add new values through a contract change.
- `source` identifies `actual_bus_simulator`, `data_demo_simulator`, or a future real edge device.
- Original GNSS coordinates and road-aligned coordinates are separate facts. The latter may be produced by map matching.

## Event — edge/simulator output

```json
{
  "event_id": "evt_01J...",
  "bus_id": "BUS-001",
  "event_type": "POTHOLE",
  "timestamp": "2026-09-20T10:30:00Z",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "road_aligned_latitude": 18.5203,
  "road_aligned_longitude": 73.8568,
  "heading_degrees": 92.4,
  "route_id": "ROUTE-A",
  "confidence": 0.91,
  "severity": "HIGH",
  "evidence_image": "evidence://BUS-001/evt_01J.jpg",
  "source": "data_demo_simulator",
  "connectivity_state": "ONLINE"
}
```

Required v1 fields: `event_id`, `bus_id`, `event_type`, `timestamp`, `latitude`, `longitude`, `confidence`, `evidence_image`, and `source`. `severity`, route, heading, road-aligned coordinates, and connectivity metadata are optional at ingestion but must retain their meaning when present. `ONLINE`/`OFFLINE` describes the edge state at event creation, not whether the server received it immediately.

## Observation — stored normalized event

An observation is the persisted representation of one received event. It retains the source event identity and must not overwrite evidence or coordinates.

```json
{
  "observation_id": "obs_01J...",
  "event_id": "evt_01J...",
  "bus_id": "BUS-001",
  "event_type": "POTHOLE",
  "timestamp": "2026-09-20T10:30:00Z",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "confidence": 0.91,
  "severity": "HIGH",
  "evidence_image": "evidence://BUS-001/evt_01J.jpg",
  "road_aligned_latitude": 18.5203,
  "road_aligned_longitude": 73.8568
}
```

## Incident — fleet-fusion output

```json
{
  "incident_id": "inc_01J...",
  "event_type": "POTHOLE",
  "status": "CANDIDATE",
  "latitude": 18.5203,
  "longitude": 73.8568,
  "observation_count": 2,
  "bus_count": 2,
  "confidence": 0.93,
  "severity": "HIGH",
  "department": "MUNICIPAL_CORPORATION",
  "first_observed_at": "2026-09-20T10:30:00Z",
  "last_observed_at": "2026-09-20T10:35:00Z"
}
```

Allowed initial incident statuses: `CANDIDATE`, `VERIFIED`, `REJECTED`, `RESOLUTION_CANDIDATE`, `RESOLVED`.

## Ticket — civic lifecycle record

```json
{
  "ticket_id": "POT-2026-000001",
  "incident_id": "inc_01J...",
  "status": "OPEN",
  "created_at": "2026-09-20T10:36:00Z",
  "updated_at": "2026-09-20T10:36:00Z"
}
```

Allowed initial ticket statuses: `OPEN`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`, `REJECTED`. Format: `POT-YYYY-XXXXXX`, with a six-digit sequence. Department routing is derived from event type and remains reviewable by an authority user.

## Severity

Severity is derived from event type, confidence, persistence, location/context, and corroborating observations. The prototype may use `LOW`, `MEDIUM`, and `HIGH`; the scoring formula is a future implementation contract and must not be inferred from `confidence` alone.

## MQTT convention

Publish v1 events to `beyonders/events/v1`. Retain no secrets in MQTT payloads. An offline edge event is stored in SQLite/WAL and later published with the same `event_id`; ingestion must be idempotent. API endpoints are intentionally not specified yet; document them here before implementation.
