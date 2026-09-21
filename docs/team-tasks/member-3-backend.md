# Member 3 — Backend

## Owns

FastAPI, contract validation, idempotent event ingestion, read APIs for incidents/tickets/dashboard use, and the boundary between MQTT ingestion and central storage.

## First deliverable

Implement the smallest contract-valid ingestion path for Data/Test/Demo Simulator events and an API response sufficient for one GIS map marker.

## Read first

- `AGENTS.md`
- `docs/api-contract.md`
- `docs/data-flow.md`
- `docs/database.md`

## Boundaries

Do not change the schema, fusion policy, event field names, or ticket lifecycle without the owners and a documentation update. The backend consumes the same contract from both simulators.

## Done when

- Input validation rejects malformed payloads clearly.
- Replayed `event_id` values are idempotent.
- Tests cover valid input, invalid input, and duplicate replay.
