# Data/Test/Demo Simulator

The **Data/Test/Demo Simulator** produces deterministic, contract-valid synthetic sensing events without computer vision (CV) dependencies. It serves as the primary integration input across the platform for independent backend development, fleet fusion testing, GIS dashboard work, and final demonstration fallback.

## Key Capabilities

1. **Zero-Dependency Core**: Executes out-of-the-box on Python 3.10+ standard library (`sqlite3`, `json`, `dataclasses`, `argparse`).
2. **Contract-Strict Compliance**: Adheres 100% to [docs/api-contract.md](../docs/api-contract.md) with canonical identifiers (`BUS-001`, `EVT-000001`), WGS84 coordinates, UTC ISO 8601 timestamps, and separation of raw GNSS vs road-aligned coordinates.
3. **Repeatable Pune Road Scenarios**:
   - **Scenario 1 (`dual_bus_pothole`)**: Two independent buses (`BUS-001`, `BUS-002`) detecting the same pothole near Goodluck Chowk on FC Road within 5 minutes.
   - **Scenario 2 (`connectivity_outage`)**: Bus `BUS-003` entering an offline underpass on Karve Road, buffering events in a local SQLite WAL outbox (`edge_outbox.db`), reconnecting, and replaying them with identical `event_id` values.
   - **Scenario 3 (`diverse_events`)**: Generates all 4 prototype event classes (`POTHOLE`, `GARBAGE`, `TRAFFIC_OBSTRUCTION`, `PEDESTRIAN_RISK`) across Pune transit corridors.
   - **Scenario 4 (`resolution_verification`)**: Initial severe defect detection on FC Road, followed 48 hours later by smooth road / post-repair evidence at the identical location for civic ticket closure.
   - **Scenario 5 (`master_demo`)**: Complete integrated sequence chaining all scenarios.
4. **Multiple Transport Modes**: `stdout` (pretty JSON or compact NDJSON), `file`, `sqlite` (WAL outbox), `http` (FastAPI POST), and `mqtt` (topic `beyonders/events/v1`).
5. **Synthetic Visual Evidence**: Generates valid JPEG evidence frames in `runtime/evidence/` with bounding boxes and HUD overlays for dashboard and ticket inspection.

---

## Directory Structure

```text
data-demo-simulator/
├── __init__.py
├── README.md                      # Documentation & usage guide
├── requirements.txt               # Optional requirements (paho-mqtt)
├── main.py                        # CLI entrypoint
├── buses/
│   ├── __init__.py
│   └── bus.py                     # Bus model, state, and BUS-XXX validation
├── routes/
│   ├── __init__.py
│   ├── route.py                   # Route, Waypoint, haversine & bearing math
│   └── pune_routes.py             # Realistic Pune road corridors (FC, JM, Karve, Shivaji)
├── gps/
│   ├── __init__.py
│   ├── coordinates.py             # WGS84 coordinate representations
│   └── simulator.py               # GPS/NavIC noise simulation & road snapping
├── events/
│   ├── __init__.py
│   ├── schema.py                  # Contract-compliant Event schema (v1 contract)
│   ├── generator.py               # Deterministic event generator
│   ├── evidence.py                # Synthetic JPEG evidence image generator
│   └── storage.py                 # SQLite WAL store-and-forward outbox
├── scenarios/
│   ├── __init__.py
│   ├── base.py                    # BaseScenario and emitters (Stdout, File, SQLite, HTTP, MQTT)
│   ├── dual_bus_pothole.py        # Scenario 1
│   ├── connectivity_outage.py     # Scenario 2
│   ├── diverse_events.py          # Scenario 3
│   ├── resolution_verification.py # Scenario 4
│   └── master_demo.py             # Scenario 5
└── tests/
    ├── __init__.py
    ├── test_contract.py           # Contract validation tests
    ├── test_gps.py                # Coordinate & route tests
    ├── test_sqlite_wal.py         # SQLite WAL outbox & replay tests
    ├── test_scenarios.py          # Deterministic scenario tests
    └── test_cli.py                # CLI and emission mode tests
```

---

## CLI Usage

### List Available Scenarios

```bash
python3 data-demo-simulator/main.py --list-scenarios
```

### Run Scenarios to stdout (Pretty JSON)

```bash
# Dual bus pothole corroboration
python3 data-demo-simulator/main.py --scenario dual_bus_pothole

# Outage & SQLite WAL replay
python3 data-demo-simulator/main.py --scenario connectivity_outage

# Diverse event classes
python3 data-demo-simulator/main.py --scenario diverse_events

# Resolution verification (before/after repair)
python3 data-demo-simulator/main.py --scenario resolution_verification

# Complete master demo sequence
python3 data-demo-simulator/main.py --scenario master_demo
```

### Stream NDJSON (Line-delimited JSON)

```bash
python3 data-demo-simulator/main.py --scenario dual_bus_pothole --mode ndjson
```

### Save to File

```bash
python3 data-demo-simulator/main.py --scenario diverse_events --mode file --output-file runtime/events.ndjson
```

### Send via HTTP to Backend Ingestion

```bash
python3 data-demo-simulator/main.py --scenario dual_bus_pothole --mode http --http-url http://localhost:8000/api/v1/events
```

### Publish to Live MQTT Broker

```bash
# Optional: install paho-mqtt if not present
pip install -r data-demo-simulator/requirements.txt

# Publish master demo events to Mosquitto with 1s delay
python3 data-demo-simulator/main.py --scenario master_demo --mode mqtt --delay 1.0
```

---

## Programmatic Python API

Any team member can import and execute scenarios directly in scripts or unit tests:

```python
from scenarios import (
    DualBusPotholeScenario,
    ConnectivityOutageScenario,
    DiverseEventsScenario,
    ResolutionVerificationScenario,
    MasterDemoScenario,
    StdoutEmitter,
)

# 1. Generate events directly as Event objects
scenario = DualBusPotholeScenario()
events = scenario.generate_events()

for evt in events:
    print(evt.event_id, evt.bus_id, evt.road_aligned_latitude, evt.road_aligned_longitude)

# 2. Run with an emitter
scenario.run(emitter=StdoutEmitter(pretty=True))
```

---

## Running Tests

Run the automated test suite with Python's standard `unittest`:

```bash
python3 -m unittest discover -s data-demo-simulator/tests -p "test_*.py" -v
```

Or from the repository root:

```bash
python3 -m unittest discover
```
