"""Main CLI entrypoint for the Actual Bus Simulator.

Supports launching single or multiple concurrent bus instances with configurable
identities, routes, ports, video inputs, and connectivity states.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Enable both direct script execution (python bus-simulator/main.py) and module execution
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from bus_instance import BusInstance
    from sensors.gnss import PUNE_ROUTES
    from ui.app import create_app
except ImportError:
    from .bus_instance import BusInstance
    from .sensors.gnss import PUNE_ROUTES
    from .ui.app import create_app

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("actual_bus_simulator")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Actual Bus Simulator - Edge AI (YOLO + ByteTrack) Sensing Pipeline"
    )
    parser.add_argument(
        "--bus-id",
        type=str,
        default="BUS-001",
        help="Bus identifier (e.g. BUS-001, BUS-002). Format: BUS-XXX.",
    )
    parser.add_argument(
        "--route",
        type=str,
        default="ROUTE-PUNE-FC",
        choices=list(PUNE_ROUTES.keys()),
        help="Pre-configured Pune route corridor to simulate.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to serve the real-time demonstration UI (default: 8001).",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind the web server (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--video",
        type=str,
        default="synthetic",
        help="Video source: 'synthetic' (default animated road), or file path (.mp4), or camera index ('0').",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=None,
        help="Optional path to custom YOLO weights (.pt, .onnx).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Start in OFFLINE mode (buffers events in local SQLite WAL outbox).",
    )
    parser.add_argument(
        "--outbox-db",
        type=str,
        default=None,
        help="Custom SQLite WAL outbox database path.",
    )
    parser.add_argument(
        "--mqtt-host",
        type=str,
        default="localhost",
        help="MQTT broker hostname (default: localhost).",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run sensing pipeline in headless background mode without web server.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=0,
        help="Run for N frames and exit (useful for automated testing/benchmarks; 0 = run indefinitely).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    initial_conn = "OFFLINE" if args.offline else "ONLINE"
    logger.info("Initializing Actual Bus Simulator for %s on %s (Mode: %s)", args.bus_id, args.route, initial_conn)

    instance = BusInstance(
        bus_id=args.bus_id,
        route_id=args.route,
        video_source=args.video,
        weights_path=args.weights,
        outbox_db=args.outbox_db,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        initial_connectivity=initial_conn,
    )

    if args.headless or args.frames > 0:
        logger.info("Running in headless pipeline mode...")
        frame_idx = 0
        try:
            while True:
                frame_idx += 1
                frame, telemetry = instance.step()
                if frame_idx % 20 == 0 or telemetry.get("latest_event_id"):
                    logger.info(
                        "[%s] Frame %d | Lat: %.5f, Lon: %.5f | Tracks: %d | Events: %d | Outbox: %d",
                        instance.bus_id,
                        frame_idx,
                        telemetry["latitude"],
                        telemetry["longitude"],
                        telemetry["active_tracks_count"],
                        telemetry["total_events_generated"],
                        telemetry["pending_outbox_count"],
                    )
                if args.frames > 0 and frame_idx >= args.frames:
                    logger.info("Reached target frame count (%d). Stopping.", args.frames)
                    break
                time.sleep(0.05)
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
        finally:
            instance.stop_loop()
        sys.exit(0)

    # Start background sensing pipeline loop
    instance.start_loop()

    # Create FastAPI web demonstration application
    app = create_app(instance)

    logger.info("Starting demonstration UI at http://%s:%d", args.host, args.port)
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    except KeyboardInterrupt:
        logger.info("Shutting down simulator...")
    finally:
        instance.stop_loop()


if __name__ == "__main__":
    main()
