# Member 4 — Database and Fleet Fusion

## Owns

PostgreSQL/PostGIS schema, geographic storage, observation-to-incident grouping, incident confidence/severity, and resolution-candidate logic.

## First deliverable

Define reviewed migrations for the shared records and a simple configurable spatial-temporal fusion policy that turns compatible observations from separate buses into one incident.

## Read first

- `AGENTS.md`
- `docs/database.md`
- `docs/fleet-fusion.md`
- `docs/api-contract.md`
- `docs/ticket-lifecycle.md`

## Boundaries

Preserve source events and evidence; fusion must never fabricate or delete observations. Do not introduce an ML fusion model or change ticket lifecycle names. Spatial/time thresholds must be documented and tested.

## Done when

- Original and road-aligned coordinates are stored separately.
- Compatible observations from `BUS-001` and `BUS-002` can form one `INC-000001`.
- Boundary and duplicate-observation tests exist.
