# Working Agreement for Humans and Coding Agents

## Project boundary

This repository is the SIH 2026 Beyonders prototype. Preserve the agreed flow:

```text
Two simulators → Edge AI (YOLO + ByteTrack) → event/evidence/GNSS/IMU
→ SQLite/WAL when offline → MQTT → FastAPI → PostgreSQL/PostGIS
→ road alignment → configurable spatial-temporal fleet fusion → severity → incident
→ authority ticket → GIS dashboard → resolution verification
```

Use `docs/api-contract.md` as the authoritative field names and state definitions.

## Before changing code

1. Read this file and the docs relevant to the issue.
2. Inspect the existing implementation and tests.
3. Implement only the requested issue; do not redesign adjacent modules.
4. Update contracts first if a cross-team interface must change, and obtain team approval in the pull request.

## Non-negotiable rules

- Do not implement feature logic until its contract and acceptance criteria are clear.
- Do not rename contract fields such as `latitude`, `longitude`, or `event_id` locally.
- Do not change database schema, MQTT topics, ticket format, or public API without updating the relevant documentation and tests.
- Keep evidence-image references, UTC timestamps, confidence, and road-aligned coordinates intact through the pipeline.
- Preserve original GNSS/GPS coordinates separately from map-matched road coordinates.
- Preserve stable `event_id` values during SQLite/WAL replay; ingestion must be idempotent.
- Keep fleet fusion simple, configurable, and explainable; do not introduce ML complexity unless the team approves it in the relevant documentation.
- Use the shared identifier formats: `BUS-001`, `EVT-000001`, `OBS-000001`, `INC-000001`, `POT-YYYY-XXXXXX`, and `WO-YYYY-XXXXXX`.
- Add or update tests for behaviour changes. Never delete tests merely to pass CI.
- Do not add large model weights, recordings, secrets, generated builds, or credentials to Git.
- Keep changes focused; do not modify unrelated files.

## Team and Git workflow

- Group 1: Member 1 owns AI/ML; Member 2 owns edge and the Actual Bus Simulator.
- Group 2: Member 3 owns backend APIs; Member 4 owns database and fleet fusion.
- Group 3: Member 5 owns GIS/dashboard; Member 6 owns integration, DevOps, CI, Docker, and the Data/Test/Demo Simulator.
- Work on `feature/*`, `fix/*`, `docs/*`, or `test/*` branches from `develop`.
- Never push directly to `main` or `develop`; use a pull request and one reviewer.
- `main` is stable/demo-ready. `develop` is the shared integration branch.

## Agent prompt pattern

For an implementation task, give the agent the GitHub Issue and list the docs to read. Ask it to explain changed files, assumptions, tests run, and limitations. AI-generated code still requires human review and understanding before merge.
