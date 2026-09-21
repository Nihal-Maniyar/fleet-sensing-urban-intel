#!/usr/bin/env python3
"""CLI Entrypoint for the Data/Test/Demo Simulator.

Usage Examples:
    # Print dual-bus pothole scenario to stdout
    python3 data-demo-simulator/main.py --scenario dual_bus_pothole

    # Output NDJSON to file
    python3 data-demo-simulator/main.py --scenario diverse_events --mode file --output-file runtime/events.ndjson

    # Test SQLite WAL outbox queueing and offline replay
    python3 data-demo-simulator/main.py --scenario connectivity_outage --mode sqlite

    # Publish to live MQTT broker
    python3 data-demo-simulator/main.py --scenario master_demo --mode mqtt --delay 1.0
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Handle directory with hyphens by aliasing module
sim_dir = Path(__file__).resolve().parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from events.storage import SQLiteOutbox
from scenarios.base import (
    BaseEmitter,
    FileEmitter,
    HTTPEmitter,
    MQTTEmitter,
    SQLiteEmitter,
    StdoutEmitter,
)
from scenarios.connectivity_outage import ConnectivityOutageScenario
from scenarios.diverse_events import DiverseEventsScenario
from scenarios.dual_bus_pothole import DualBusPotholeScenario
from scenarios.master_demo import MasterDemoScenario
from scenarios.resolution_verification import ResolutionVerificationScenario

SCENARIO_REGISTRY = {
    "dual_bus_pothole": DualBusPotholeScenario,
    "connectivity_outage": ConnectivityOutageScenario,
    "diverse_events": DiverseEventsScenario,
    "resolution_verification": ResolutionVerificationScenario,
    "master_demo": MasterDemoScenario,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic, contract-valid Data/Test/Demo Simulator for Fleet Sensing Urban Intelligence."
    )

    parser.add_argument(
        "--scenario",
        type=str,
        choices=list(SCENARIO_REGISTRY.keys()) + ["all"],
        default="dual_bus_pothole",
        help="Scenario to run (default: dual_bus_pothole).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["stdout", "ndjson", "file", "sqlite", "http", "mqtt"],
        default="stdout",
        help="Event transport target mode (default: stdout).",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="runtime/simulated_events.ndjson",
        help="Output file path when --mode file or ndjson is chosen.",
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default="runtime/edge_outbox.db",
        help="SQLite WAL outbox database file path (default: runtime/edge_outbox.db).",
    )
    parser.add_argument(
        "--http-url",
        type=str,
        default="http://localhost:8000/api/v1/events",
        help="Target backend HTTP ingestion endpoint (default: http://localhost:8000/api/v1/events).",
    )
    parser.add_argument(
        "--mqtt-host",
        type=str,
        default=os.getenv("MQTT_HOST", "localhost"),
        help="MQTT broker hostname (default: localhost or env MQTT_HOST).",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=int(os.getenv("MQTT_PORT", "1883")),
        help="MQTT broker port (default: 1883 or env MQTT_PORT).",
    )
    parser.add_argument(
        "--mqtt-topic",
        type=str,
        default=os.getenv("MQTT_TOPIC_PREFIX", "beyonders/events/v1"),
        help="MQTT topic to publish to (default: beyonders/events/v1).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay in seconds between event emissions for playback (default: 0.0).",
    )
    parser.add_argument(
        "--no-evidence",
        action="store_true",
        help="Disable creating actual JPEG evidence image files on disk.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List available scenarios and descriptions, then exit.",
    )
    return parser


def create_emitter(args: argparse.Namespace) -> BaseEmitter:
    """Instantiate appropriate emitter based on CLI arguments."""
    if args.mode == "stdout":
        return StdoutEmitter(pretty=True, ndjson=False)
    elif args.mode == "ndjson":
        return StdoutEmitter(pretty=False, ndjson=True)
    elif args.mode == "file":
        fmt = "json" if args.output_file.endswith(".json") else "ndjson"
        return FileEmitter(output_path=args.output_file, format=fmt)
    elif args.mode == "sqlite":
        return SQLiteEmitter(db_path=args.sqlite_path)
    elif args.mode == "http":
        return HTTPEmitter(endpoint_url=args.http_url)
    elif args.mode == "mqtt":
        return MQTTEmitter(host=args.mqtt_host, port=args.mqtt_port, topic=args.mqtt_topic)
    else:
        raise ValueError(f"Unsupported mode: {args.mode}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_scenarios:
        sys.stdout.write("Available Simulator Scenarios:\n\n")
        for key, cls_type in SCENARIO_REGISTRY.items():
            sys.stdout.write(f"  • {key:<26}: {cls_type.description}\n")
        return 0

    emitter = create_emitter(args)
    auto_evidence = not args.no_evidence

    scenarios_to_run = (
        list(SCENARIO_REGISTRY.keys()) if args.scenario == "all" else [args.scenario]
    )

    total_emitted = 0
    for sc_name in scenarios_to_run:
        cls_type = SCENARIO_REGISTRY[sc_name]
        if sc_name == "connectivity_outage":
            scenario = cls_type(auto_generate_evidence=auto_evidence, db_path=args.sqlite_path)
        elif sc_name == "master_demo":
            scenario = cls_type(auto_generate_evidence=auto_evidence, db_path=args.sqlite_path)
        else:
            scenario = cls_type(auto_generate_evidence=auto_evidence)

        events = scenario.run(emitter=emitter, delay_seconds=args.delay)
        total_emitted += len(events)

    if args.mode not in ("stdout", "ndjson"):
        sys.stdout.write(
            f"Successfully executed scenario '{args.scenario}' with {total_emitted} events (mode: {args.mode}).\n"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
