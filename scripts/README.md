# Scripts Directory

This directory contains utility entrypoints for running and managing the Fleet Sensing Urban Intelligence platform.

## Production End-to-End Runner

To run the complete system end-to-end in real time:

```bash
# Run using the virtual environment
./.venv/bin/python run_project.py

# Or via the scripts entrypoint:
./.venv/bin/python scripts/run_project.py
```

### Execution Architecture

The master runner orchestrates the complete production lifecycle:

1. **FastAPI Backend & GIS Server** (`http://127.0.0.1:8000`):
   - Healthcheck polled at `/health` until confirmed operational.
   - Dual-transport ingestion (`POST /events` + MQTT broker topic `fleet/events/#`).
   - Fleet Telemetry ingestion (`POST /api/v1/fleet/telemetry`) updating live bus GPS positions.
   - Real-time WebSocket multiplexing at `/ws/stream` broadcasting incidents, fleet updates, and metrics.
   - GIS Dashboard served directly at `http://127.0.0.1:8000/dashboard`.

2. **Actual Bus Simulator 1 (`BUS-001`)** on port `8001`:
   - Runs Edge AI sensing pipeline (YOLO + ByteTrack tracking) along corridor `ROUTE-PUNE-FC`.
   - Generates canonical event IDs (`EVT-010001+`).
   - Streams live GNSS telemetry and detected road anomalies directly to the backend.

3. **Staggered Delay (`--stagger-seconds 6.0`)**:
   - Holds before launching Bus 2 to create realistic spatial-temporal separation on the same corridor.

4. **Actual Bus Simulator 2 (`BUS-002`)** on port `8002`:
   - Runs along the same corridor (`ROUTE-PUNE-FC`) behind Bus 1.
   - Generates canonical event IDs (`EVT-020001+`).
   - Emits observations for the same road defects, triggering the **Fleet Fusion Engine** to correlate observations across buses, elevate confidence, and generate official tickets.

5. **Live GIS Dashboard**:
   - Opens automatically in the default browser at `http://127.0.0.1:8000/dashboard`.
   - Starts in pure real-time live mode with zero seed data, visualizing live buses moving along the Pune corridors, active detections, and fused incident tickets as they occur.

### Command-Line Options

```text
--backend-host HOST      Host address (default: 127.0.0.1)
--backend-port PORT      Backend port (default: 8000)
--bus1-id ID             Bus 1 identifier (default: BUS-001)
--bus2-id ID             Bus 2 identifier (default: BUS-002)
--bus1-port PORT         Bus 1 UI port (default: 8001)
--bus2-port PORT         Bus 2 UI port (default: 8002)
--route ROUTE            Pune corridor (default: ROUTE-PUNE-FC)
--stagger-seconds SECS   Stagger delay between buses (default: 6.0)
--no-browser             Do not auto-open the browser dashboard
--headless               Run bus simulators in headless pipeline mode
```

### Clean Teardown

Pressing `Ctrl+C` sends graceful termination signals to the backend and all running bus simulators, ensuring no background processes or ports (`8000`, `8001`, `8002`) are left orphaned.
