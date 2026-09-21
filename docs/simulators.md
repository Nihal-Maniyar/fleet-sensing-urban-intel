# Simulators

## Actual Bus Simulator

Represents the real bus sensing path. It may use prerecorded video or a camera feed plus simulated GNSS/NavIC, IMU, bus identity, route, and connectivity. It is expected to pass through YOLO, ByteTrack, temporal event generation, evidence capture, GPS/road-aligned coordinate assignment, and online/offline transmission before publishing to MQTT.

## Data/Test/Demo Simulator

Generates deterministic, contract-valid sample events without CV. It is the first integration input and must support repeatable route scenarios: two buses independently observing the same pothole, a connectivity outage followed by replay, different event classes, and later observations supporting resolution verification.

Both simulators publish the same v1 event contract. They differ only in `source` and how an event is produced; both must preserve stable `event_id` values across retries/replay.
