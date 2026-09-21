# Demo Plan

## Repeatable target story

1. Start local PostGIS and MQTT infrastructure.
2. Run the Data/Test/Demo Simulator with at least two buses observing one pothole near the same road location.
3. Show valid event ingestion, evidence references, original/road-aligned coordinates, and map placement.
4. Toggle connectivity off; show an event stored in the edge SQLite/WAL queue, then reconnect and replay it exactly once by `event_id`.
5. Show simple spatial-temporal fusion producing a verified incident, severity, and suggested authority department.
6. Show a linked ticket, for example `POT-2026-000001`, with a Google Maps link and the official lifecycle: `REPORTED` → `ACKNOWLEDGED` → `IN_PROGRESS` → `RESOLVED`.
7. Replay later observations at the same location to show a resolution candidate and authority closure.
8. Optionally replay the same scenario through the Actual Bus Simulator once the YOLO + ByteTrack path is ready.

The demo must still work with the Data/Test/Demo Simulator if camera hardware or a model is unavailable.
