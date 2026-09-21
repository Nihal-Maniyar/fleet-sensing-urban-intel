# Simulators

## Actual Bus Simulator

Represents one real bus sensing path. One running instance is one bus, and multiple instances must be able to run simultaneously. It may use prerecorded video or a camera feed plus simulated GNSS/NavIC, IMU, bus identity, route, and connectivity. It is expected to pass through YOLO, ByteTrack, temporal event generation, evidence capture, GPS/road-aligned coordinate assignment, and online/offline transmission before publishing to MQTT.

Its demonstration UI must show the current video feed, detection boxes/labels/confidence, ByteTrack IDs, bus ID, location, event information, and connection state. It is not a fake-event generator.

## Data/Test/Demo Simulator

Generates deterministic, contract-valid sample events without CV. It is the first integration input and must support repeatable route scenarios: two buses independently observing the same pothole, a connectivity outage followed by replay, different event classes, and later observations supporting resolution verification. It must be usable by every team member for independent development, integration testing, dashboard work, and final-demo fallback.

Both simulators publish the same v1 event contract. They differ only in `source` and how an event is produced; both must preserve stable `event_id` values across retries/replay.
