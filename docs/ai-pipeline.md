# AI and Edge Sensing Pipeline

The AI and Edge Sensing Pipeline represents the Group 1 subsystem of the **Fleet Sensing Urban Intel** platform (SIH 2026). It runs directly on edge compute nodes aboard municipal public transit buses (e.g. Pune PMPML routes), processing video feeds from forward-facing cameras in real-time to detect road surface distress and urban anomalies, track them temporally, capture evidence frames, correlate detections with GNSS/IMU telemetry, and publish standardized events via MQTT or SQLite/WAL offline storage.

---

## 1. End-to-End Pipeline Architecture

```text
┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ Camera / Video │ ───> │ Sequential Frame Reader │ ───> │  YOLO Pothole Detector  │
│ Stream Source  │      │   (Generator / OpenCV)  │      │ (CUDA / MPS / CPU Auto) │
└────────────────┘      └─────────────────────────┘      └─────────────────────────┘
                                                                      │
                                                                      ▼
┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ Evidence Image │ <─── │   Temporal Event Engine │ <─── │  ByteTrack Associator   │
│ Capture Engine │      │  (Dedup & Persistence)  │      │  (Kalman Filter States) │
└────────────────┘      └─────────────────────────┘      └─────────────────────────┘
        │                            │
        │ File path                  │ Canonical Event
        ▼                            ▼
┌────────────────────────────────────────────────────────┐
│             Bus Instance Edge Coordinator              │
│       (Correlates with GPS Telemetry & UTC Time)       │
└────────────────────────────────────────────────────────┘
        │
        ├─────────────────────────────┬─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────┐             ┌───────────────┐             ┌───────────────┐
│ SQLite / WAL  │ (Offline)   │ MQTT Broker   │ (Online)    │ Annotated HUD │
│ Local Outbox  │             │ Topic Publish │             │ Video Output  │
└───────────────┘             └───────────────┘             └───────────────┘
```

The pipeline strictly guarantees:
1. **Streaming memory footprint**: Frames are processed sequentially as generators; full video files are never buffered into RAM.
2. **Deterministic deduplication**: Raw detections occurring across consecutive frames for the same physical defect are assigned a continuous track ID by ByteTrack. The Event Engine filters transient false positives and emits exactly **one** canonical event per physical anomaly.
3. **API Contract integrity**: All generated events strictly conform to `docs/api-contract.md` field specifications (`event_id`, `bus_id`, `event_type`, `confidence`, `latitude`, `longitude`, `timestamp`, `evidence_image`, `source`).
4. **Idempotence & offline resilience**: SQLite/WAL preserves stable `event_id` keys during network disconnects and replays them to MQTT without duplicates.

---

## 2. Pipeline Stages

### Stage 1: Video Source & Frame Acquisition
- Implemented in `bus-simulator/camera/stream.py` and exposed via `edge.camera`.
- **`VideoStreamSource`**: Abstract base class defining `read_frame()`, `stream()`, `get_metadata()`, and release lifecycle.
- **`OpenCVFileStream`**: Sequential reader for recorded video files (MP4, AVI) supporting loop playback, frame index tracking, resolution, and native FPS extraction.
- **`SyntheticCameraStream`**: Procedural frame generator for testing and CI without requiring physical cameras or video files. Injects deterministic pothole markers at specified intervals.

### Stage 2: YOLO Object Detection
- Implemented in `bus-simulator/detection/yolo.py` and exposed via `edge.detection`.
- **`YoloDetector`**: Encapsulates Ultralytics YOLOv8/v11 models.
  - Automatic hardware acceleration: detects and selects `cuda` (NVIDIA), `mps` (Apple Silicon), or `cpu`.
  - Offline isolation: defaults `YOLO_CONFIG_DIR=runtime/.ultralytics` and `YOLO_OFFLINE=true` to prevent external network calls and ensure sandboxed reliability.
  - Normalizes model detection classes to standard API contract types (`POTHOLE`).
  - Supports synthetic/mock detection injection for automated test suites.

### Stage 3: ByteTrack Multi-Object Tracking
- Implemented in `bus-simulator/tracking/byte_tracker.py` and exposed via `edge.tracking`.
- **`ByteTracker`**: Pure-Python/NumPy implementation of the two-stage ByteTrack association algorithm with Kalman filter motion prediction.
  - Avoids external compiled C dependencies (`lap`), enabling seamless cross-platform execution on edge devices.
  - Stage 1: Associates high-confidence detections (`track_thresh >= 0.5`) with tracked trajectories via Hungarian matching on IoU distances.
  - Stage 2: Associates remaining unconfirmed/low-confidence detections (`0.1 <= conf < track_thresh`) with unmatched tracks to maintain continuity during visual occlusion or motion blur.
  - Manages track states: `New`, `Tracked`, `Lost`, `Removed`.

### Stage 4: Temporal Event Decision Engine
- Implemented in `bus-simulator/events/engine.py` and exposed via `edge.events`.
- **`EventEngine`**: Enforces civic observation policies so that individual video frames do not flood the ingestion pipeline.
  - **Persistence threshold**: Requires a defect to be tracked across at least $N$ consecutive frames (configurable, default 3) before confirming an event.
  - **Single canonical event emission**: Exactly one event is triggered per active track ID. Subsequent sightings update trajectory metrics but do not re-emit duplicate events.
  - **Cooldown window**: Enforces a time/frame buffer preventing re-triggering in the same spatial vicinity.
  - **Confidence gate**: Enforces `min_confidence` (default 0.50) distinct from raw detection threshold (0.25).

### Stage 5: Evidence Capture
- Implemented in `bus-simulator/evidence/capture.py` and exposed via `edge.evidence`.
- **`EvidenceCapture`**: Generates high-visibility JPG snapshots stored in `runtime/evidence/` or configured path.
  - Bounding box annotation with neon bounding rectangle (`#00E5FF` / `#00D26A`), defect label, confidence, and track ID.
  - Filename matches event contract: `EVT-XXXXXX.jpg` (or UUID fallback), referenced directly in event payload `evidence_image`.

### Stage 6: Telemetry Correlation & Ingestion
- Implemented in `bus-simulator/bus_instance.py`.
- Merges vision event with real-time GPS telemetry (`latitude`, `longitude`, `altitude`, `speed`, `heading`) and ISO 8601 UTC timestamp.
- Dispatches event to `SQLiteOutbox` (`runtime/bus_<bus_id>_outbox.db`) and publishes to MQTT topic:
  `fleet/sensing/<bus_id>/pothole`

---

## 3. High-Level AI Orchestrator (`ai/`)

The `ai/` package provides a clean, unified top-level interface for running the complete sensing pipeline:

```python
from ai import AIPipeline

# Initialize pipeline with custom thresholds and device
pipeline = AIPipeline(
    model_path="models/best.pt",
    model_confidence=0.25,
    event_confidence=0.50,
    device="mps",  # or "cuda", "cpu"
)

# Process a video file, generate evidence, and output annotated HUD video
events = pipeline.process_video(
    video_path="data/videos/road_video.mp4",
    output_path="runtime/output/annotated_run.mp4",
    max_frames=120,
    bus_id="BUS-001",
    gps_coords=(18.5204, 73.8567),
)

for event in events:
    print(f"Detected {event['event_id']}: {event['event_type']} "
          f"(confidence: {event['confidence']:.2f}) -> {event['evidence_image']}")
```

---

## 4. Configuration and Environment Variables

The pipeline is configured via environment variables or CLI arguments. Defaults are centralized in `ai/config.py`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MODEL_PATH` | `models/pothole_detector.pt` | Path to YOLO `.pt` weights file |
| `MODEL_CONFIDENCE_THRESHOLD` | `0.25` | Minimum raw YOLO detection confidence |
| `EVENT_CONFIDENCE_THRESHOLD` | `0.50` | Minimum confidence required to emit a confirmed event |
| `DEVICE` | Auto (`cuda` / `mps` / `cpu`) | PyTorch compute accelerator |
| `TRACKER_TYPE` | `bytetrack` | Tracking algorithm |
| `TRACK_THRESH` | `0.50` | High-confidence threshold for ByteTrack Stage 1 |
| `TRACK_BUFFER` | `30` | Maximum frames to keep lost tracks alive |
| `MATCH_THRESH` | `0.80` | IoU cost threshold for track matching |
| `EVIDENCE_STORAGE_PATH` | `runtime/evidence` | Directory for evidence snapshot files |
| `VIDEO_OUTPUT_PATH` | `runtime/output` | Directory for annotated video recordings |
| `YOLO_CONFIG_DIR` | `runtime/.ultralytics` | Isolated Ultralytics configuration directory |
| `YOLO_OFFLINE` | `true` | Disables Ultralytics analytics and web requests |

---

## 5. CLI Usage Examples

### Running the Bus Simulator with Recorded Road Video
```bash
python bus-simulator/main.py \
  --bus-id BUS-001 \
  --video data/videos/road_video.mp4 \
  --weights models/best.pt \
  --confidence 0.25 \
  --event-confidence 0.50 \
  --device mps \
  --headless \
  --frames 100
```

### Running with Synthetic Camera Stream (No Video File Needed)
```bash
python bus-simulator/main.py \
  --bus-id BUS-002 \
  --synthetic \
  --fps 10 \
  --headless \
  --frames 50
```

### Generating Annotated Video Output
```bash
python bus-simulator/main.py \
  --bus-id BUS-001 \
  --video data/videos/road_video.mp4 \
  --weights models/best.pt \
  --output-video runtime/output/hud_run.mp4 \
  --headless \
  --frames 120
```

---

## 6. Event Schema (`api-contract.md` v1)

Events generated by the AI pipeline adhere strictly to the SIH 2026 schema:

```json
{
  "event_id": "EVT-000001",
  "bus_id": "BUS-001",
  "event_type": "POTHOLE",
  "confidence": 0.912,
  "latitude": 18.52043,
  "longitude": 73.85674,
  "timestamp": "2026-09-24T18:32:00.123456Z",
  "evidence_image": "runtime/evidence/EVT-000001.jpg",
  "source": "ACTUAL_BUS"
}
```

---

## 7. Multi-Bus Independence and Fleet Considerations

- **Independent Tracking State**: Each `BusInstance` edge runner maintains its own `ByteTracker` instance, Kalman filter matrices, and `EventEngine` memory.
- **Independent Outbox**: Each bus persists events to an isolated SQLite WAL database (`runtime/bus_<bus_id>_outbox.db`), preventing database locks between concurrent bus simulators.
- **Central Fusion**: Individual bus event IDs (`EVT-XXXXXX`) are ingested centrally and correlated across trips/buses into verified observations (`OBS-XXXXXX`) and civic incidents (`INC-XXXXXX`) by the backend fleet fusion engine.

---

## 8. Verification and Test Suites

The pipeline includes comprehensive unit and integration tests:

### Running AI Pipeline Tests
```bash
pytest -v tests/test_ai_pipeline.py
```
Tests verify:
- Sequential frame streaming without whole-file memory allocation.
- Correct bounding box translation and normalization in `Detection`.
- ByteTrack track-ID assignment, persistence, and state transitions.
- Duplicate event suppression (exactly 1 event per track ID across multiple sightings).
- Evidence snapshot image generation on disk.
- Contract compliance of generated event dictionary.
- Multi-bus instance isolation (`BUS-001` vs `BUS-002`).

### Running Full Project Test Suite
```bash
pytest -v
python3 -m unittest discover -s bus-simulator/tests -v
```
All **82 pytest tests** and **20 bus-simulator unittest tests** pass cleanly.
