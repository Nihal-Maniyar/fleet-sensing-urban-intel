# Working Agreement for Humans and Coding Agents

## Project boundary

This repository is the SIH 2026 Beyonders prototype. Preserve the agreed flow:

```text
Two simulators → Edge AI (YOLO + ByteTrack) → event/evidence/GNSS/IMU
→ SQLite/WAL when offline → MQTT → FastAPI → PostgreSQL/PostGIS
→ map matching → ST-DBSCAN/Bayesian fleet fusion → severity → incident
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
- Treat ST-DBSCAN, Bayesian evidence update, severity, map matching, and resolution verification as documented prototype policies—not invisible magic.
- Add or update tests for behaviour changes. Never delete tests merely to pass CI.
- Do not add large model weights, recordings, secrets, generated builds, or credentials to Git.
- Keep changes focused; do not modify unrelated files.

## Team and Git workflow

- Group 1 (Members 1 & 2): AI/CV, tracking, edge-event inputs.
- Group 2 (Members 3 & 4): simulators, MQTT/ingestion, backend and database integration.
- Group 3 (Members 5 & 6): fleet fusion, ticket lifecycle, GIS dashboard.
- Work on `feature/*`, `fix/*`, `docs/*`, or `test/*` branches from `develop`.
- Never push directly to `main` or `develop`; use a pull request and one reviewer.
- `main` is stable/demo-ready. `develop` is the shared integration branch.

## Agent prompt pattern

For an implementation task, give the agent the GitHub Issue and list the docs to read. Ask it to explain changed files, assumptions, and tests run. AI-generated code still requires human review and understanding before merge.
