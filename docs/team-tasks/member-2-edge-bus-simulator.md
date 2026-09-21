# Member 2 — Edge and Actual Bus Simulator

## Owns

The Actual Bus Simulator, video input, ByteTrack integration, edge event packaging, GNSS/GPS context, evidence capture, MQTT publishing, and SQLite/WAL buffering.

## First deliverable

Create one-bus simulator behavior using the approved detection interface. One instance represents one `BUS-001`-style bus; multiple instances must later run independently against the same central contract.

## Read first

- `AGENTS.md`
- `docs/simulators.md`
- `docs/ai-pipeline.md`
- `docs/api-contract.md`
- `docs/data-flow.md`

## Boundaries

Do not decide fleet verification, ticket status, or dashboard behavior. Detection is not automatically an event. Preserve the stable event ID during offline replay and use the exact shared field names.

## Done when

- The UI visibly shows video, boxes/labels, confidence, track IDs, bus ID, location, event details, and connectivity state.
- A valid event has an evidence-image reference and the shared contract fields.
- The same event can be replayed after reconnect without creating a duplicate central observation.
