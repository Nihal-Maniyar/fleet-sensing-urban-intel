# Member 5 — GIS Dashboard

## Owns

React/Vite/Leaflet dashboard, bus/event/incident/ticket views, evidence display, road-aligned map presentation, and authority lifecycle controls.

## First deliverable

Build a contract-driven map view using mock or API data that displays a Pune road-aligned incident, its evidence, and its linked ticket.

## Read first

- `AGENTS.md`
- `docs/api-contract.md`
- `docs/prototype-scope.md`
- `docs/ticket-lifecycle.md`
- `docs/demo.md`

## Boundaries

Do not invent alternate IDs, coordinates, status names, or backend fields. Do not make ticket transitions outside `REPORTED` → `ACKNOWLEDGED` → `IN_PROGRESS` → `RESOLVED`.

## Done when

- A real-road map location, evidence image, ticket status, and Google Maps link are visible.
- The primary pothole scenario is understandable to a judge without technical logs.
- The dashboard can switch its data source between actual-bus and demo-simulator contract data without a UI redesign.
