# Member 6 — Integration, DevOps, and Demo Simulator

## Owns

Git/GitHub workflow, GitHub Actions, Docker Compose infrastructure, Data/Test/Demo Simulator, integration tests, and the repeatable demo environment.

## First deliverable

Maintain the repository foundation and implement deterministic demo scenarios that publish the same contract as the Actual Bus Simulator: one pothole observed by multiple buses, offline replay, ticket creation, and resolution evidence.

## Read first

- `AGENTS.md`
- `docs/development.md`
- `docs/simulators.md`
- `docs/api-contract.md`
- `docs/demo.md`

## Boundaries

Do not become the owner of every feature. Do not modify AI, fusion, database, or dashboard contracts without their owners. Keep CI simple until real tests and build definitions exist.

## Done when

- CI validates repository contracts and later activates module checks when configured.
- Docker Compose provides only PostGIS and MQTT until application containers have real definitions.
- The demo simulator is a first-class fallback that requires no central-system architecture change.
