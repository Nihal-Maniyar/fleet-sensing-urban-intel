# Actual Bus Simulator

The **Actual Bus Simulator** represents the real bus sensing path for the Beyonders prototype, executing the complete edge AI computer-vision pipeline as specified in [docs/simulators.md](../docs/simulators.md), [docs/ai-pipeline.md](../docs/ai-pipeline.md), and [docs/api-contract.md](../docs/api-contract.md).

One running instance corresponds to one physical bus (e.g. `BUS-001`), and multiple instances can execute simultaneously on distinct routes and network ports.

```text
Camera / Video Stream (Synthetic Road / MP4 / Webcam)
         ↓
Frame Preprocessing & Normalization
         ↓
YOLO Object Detection (Potholes, Obstructions, Hazards)
         ↓
ByteTrack Multi-Object Tracking (Two-stage association + Kalman Filter)
         ↓
Temporal Event Engine (Persistence rules, suppression, peak confidence)
         ↓
Evidence Capture (Annotated JPEG snapshot in runtime/evidence/EVT-XXXXXX.jpg)
         ↓
GNSS / NavIC + 6-DOF IMU Telemetry (Raw vs Road-aligned coords, physical shock)
         ↓
SQLite WAL Outbox Buffer (when offline) ─── Replay ───→ MQTT (`beyonders/events/v1`)
         ↓
Interactive Real-Time Demonstration Web UI (MJPEG + WebSockets)
```

---

## Key Capabilities

1. **Zero-Binary Out-of-the-Box Operation**:
   - In adherence with `AGENTS.md` ("Do not add large model weights, recordings, secrets, generated builds, or credentials to Git"), the simulator includes a built-in computer-vision feature detector and dynamic procedural road generator.
   - It runs immediately with zero external weight downloads.
   - If custom YOLOv8 weights (`.pt`, `.onnx`) are supplied via `--weights`, or custom video footage is supplied via `--video`, the pipeline seamlessly transitions to model execution.

2. **Authentic ByteTrack Tracking**:
   - Full 2-stage association algorithm: high-confidence detection matching followed by low-confidence detection matching to prevent track loss during occlusions or shadows.
   - Kalman filter bounding-box state estimation ($[x, y, a, h, \dot{x}, \dot{y}, \dot{a}, \dot{h}]$).
   - Preserves continuous track IDs across frames.

3. **Temporal Event Rules & Suppression**:
   - Prevents every video frame from generating an independent event.
   - Enforces a minimum track persistence threshold ($\ge 3$ frames) before generating an event candidate.
   - Emits exactly **one** canonical event per unique track ID.
   - Spatial-temporal suppression suppresses redundant events within 15 meters for the same bus.

4. **Multi-Instance Support**:
   - Multiple buses can run concurrently side-by-side with separate identity, route, outbox databases, and web ports:
     - Bus 1: `--bus-id BUS-001 --route ROUTE-PUNE-FC --port 8001`
     - Bus 2: `--bus-id BUS-002 --route ROUTE-PUNE-JM --port 8002`

5. **GNSS / NavIC & 6-DOF IMU Coupling**:
   - Authentic Pune road corridors (`ROUTE-PUNE-FC`, `ROUTE-PUNE-JM`, `ROUTE-PUNE-KARVE`, `ROUTE-PUNE-SHIVAJI`).
   - Separate raw GNSS coordinates (with realistic satellite noise) and road-aligned coordinates.
   - Accelerometer ($a_x, a_y, a_z$) and gyroscope ($\omega_x, \omega_y, \omega_z$) with coupled vertical shock spikes when passing over road defects.

6. **SQLite WAL Outbox & MQTT Transport**:
   - Local store-and-forward outbox using Write-Ahead Logging (`runtime/bus_{bus_id}_outbox.db`).
   - Idempotent ingestion: immutable `event_id` is preserved during offline buffering and subsequent MQTT replay.
   - Publishes to `beyonders/events/v1` with QoS 1.

7. **Rich Demonstration UI**:
   - Live MJPEG stream showing real-time camera view with YOLO bounding boxes, class labels, confidence, and ByteTrack track IDs (`#ID`).
   - Telemetry HUD: Bus ID, route, speed, heading, raw vs snapped GPS coordinates.
   - IMU live gauges with shock detector.
   - One-click connectivity toggle between **ONLINE** and **OFFLINE**.
   - Live contract events table with modal preview of captured evidence images.

---

## Directory Structure

```text
bus-simulator/
├── __init__.py
├── README.md                      # Documentation & usage guide
├── requirements.txt               # Dependencies
├── main.py                        # CLI entrypoint
├── bus_instance.py                # Single bus sensing pipeline coordinator
├── camera/
│   ├── __init__.py
│   └── stream.py                  # Procedural road stream & OpenCV video capture
├── detection/
│   ├── __init__.py
│   ├── interface.py               # Detection dataclass & IoU math
│   └── yolo.py                    # YOLO detector with CV fallback
├── tracking/
│   ├── __init__.py
│   └── byte_tracker.py            # ByteTrack 2-stage association & Kalman filter
├── events/
│   ├── __init__.py
│   ├── schema.py                  # API contract v1 Event schema
│   └── engine.py                  # Temporal persistence & suppression engine
├── sensors/
│   ├── __init__.py
│   ├── gnss.py                    # Pune route coordinates & NavIC satellite noise
│   └── imu.py                     # 6-DOF IMU accelerometer & pothole shock simulation
├── evidence/
│   ├── __init__.py
│   └── capture.py                 # Evidence frame capture & HUD annotation
├── transport/
│   ├── __init__.py
│   ├── outbox.py                  # SQLite WAL store-and-forward outbox
│   └── mqtt_client.py             # Paho-MQTT publisher & outbox replayer
├── ui/
│   ├── __init__.py
│   ├── app.py                     # FastAPI web server, MJPEG & WebSockets
│   └── static/
│       └── index.html             # Demonstration UI dashboard
└── tests/
    ├── __init__.py
    ├── test_contract.py           # Contract compliance tests
    ├── test_camera.py             # Video stream tests
    ├── test_detection.py          # Detection interface tests
    ├── test_bytetrack.py          # ByteTrack multi-object tracking tests
    ├── test_temporal_engine.py    # Temporal persistence & deduplication tests
    ├── test_sensors.py            # GNSS & IMU dynamic physics tests
    ├── test_sqlite_wal.py         # SQLite WAL outbox & idempotency tests
    ├── test_evidence.py           # Evidence image generation tests
    └── test_multi_instance.py     # Concurrent multi-bus tests
```

---

## Getting Started

### 1. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r bus-simulator/requirements.txt
```

### 2. Launching the Simulator

#### Launch Bus 1 (Default):
```bash
python bus-simulator/main.py --bus-id BUS-001 --route ROUTE-PUNE-FC --port 8001
```
Open your browser at **http://localhost:8001** to view the live dashboard.

#### Launch Bus 2 Simultaneously:
In a second terminal:
```bash
python bus-simulator/main.py --bus-id BUS-002 --route ROUTE-PUNE-JM --port 8002
```
Open **http://localhost:8002** to observe the second bus operating independently on JM Road.

### 3. CLI Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `--bus-id` | string | `BUS-001` | Bus identifier in `BUS-XXX` format |
| `--route` | string | `ROUTE-PUNE-FC` | Route corridor (`ROUTE-PUNE-FC`, `ROUTE-PUNE-JM`, `ROUTE-PUNE-KARVE`, `ROUTE-PUNE-SHIVAJI`) |
| `--port` | int | `8001` | Web demonstration UI port |
| `--host` | string | `127.0.0.1` | Host address to bind |
| `--video` | string | `synthetic` | Video input: `synthetic`, path to `.mp4` file, or webcam index (`0`) |
| `--weights` | string | `None` | Optional path to custom YOLO weights (`.pt`, `.onnx`) |
| `--offline` | flag | `False` | Start in OFFLINE mode (buffers events in SQLite WAL) |
| `--outbox-db` | string | auto | Custom SQLite WAL outbox database file path |
| `--mqtt-host` | string | `localhost` | MQTT broker hostname |
| `--mqtt-port` | int | `1883` | MQTT broker port |
| `--headless` | flag | `False` | Run headlessly without web server |
| `--frames` | int | `0` | Run for N frames and exit (0 = infinite) |

---

## Running Automated Tests

Run the test suite using the virtual environment:
```bash
python -m unittest discover -s bus-simulator/tests -v
```
