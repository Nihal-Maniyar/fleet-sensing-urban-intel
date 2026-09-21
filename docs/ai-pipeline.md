# AI and Edge Pipeline

The intended actual-bus sequence is:

```text
camera/video → frame preprocessing → lightweight YOLO → ByteTrack → temporal event rules → evidence image + GNSS/GPS/IMU → SQLite/WAL or MQTT event
```

For the first reliable demo, pothole detection is the primary story. The intended prototype class set also includes road damage, garbage/waste, waterlogging, illegal parking, vehicles, and persons. Vehicle/person tracks can support density and safety views; they are not automatically civic incidents.

The event decision policy must prevent every video frame from becoming a separate event. ByteTrack supplies object continuity; temporal persistence, suppression, evidence capture, and event deduplication belong to the event engine. Quantized/lightweight YOLO with ONNX Runtime or TensorRT is the intended edge optimization path, not a requirement to commit model binaries now.

GNSS/NavIC supplies position and the IMU helps account for motion/perspective changes. Map matching later turns noisy positions into road-aligned coordinates.

The edge layer publishes the contract in [api-contract.md](api-contract.md). It does not perform fleet-level verification or create tickets. If connectivity is unavailable, SQLite/WAL stores events for later MQTT synchronization. Store model weights, videos, and generated evidence outside Git unless the team explicitly approves a small test fixture.
