#!/usr/bin/env python3
"""Master End-to-End Project Runner for Fleet Sensing Urban Intelligence Platform.

Execution Flow:
1. Bootstraps the FastAPI backend & GIS web server on port 8000.
2. Verifies backend health and API responsiveness.
3. Starts Actual Bus Simulator 1 (BUS-001) on the specified route corridor.
4. Waits for a configurable staggered delay to establish spatial-temporal separation.
5. Starts Actual Bus Simulator 2 (BUS-002) on the same route corridor for fleet fusion.
6. Launches the GIS Dashboard in the default web browser (unless --no-browser is set).
7. Multiplexes logs from all services and guarantees clean shutdown on SIGINT/SIGTERM.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from subprocess import PIPE, Popen

# Root directory of the repository
REPO_ROOT = Path(__file__).resolve().parent


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def print_banner() -> None:
    banner = f"""
{Colors.CYAN}{Colors.BOLD}================================================================================
  FLEET SENSING URBAN INTELLIGENCE PLATFORM
================================================================================{Colors.RESET}
  Real-Time Edge AI Sensing (YOLO + ByteTrack) -> Dual-Transport Ingestion
  -> Spatial-Temporal Fleet Fusion -> Verified Incident Tickets -> Live GIS
{Colors.CYAN}================================================================================{Colors.RESET}
"""
    print(banner, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="End-to-end master runner for the Fleet Sensing Urban Intelligence system."
    )
    parser.add_argument(
        "--backend-host",
        type=str,
        default="127.0.0.1",
        help="Host address for backend and simulators (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--backend-port",
        type=int,
        default=8000,
        help="Port for the FastAPI backend and GIS dashboard (default: 8000).",
    )
    parser.add_argument(
        "--bus1-id",
        type=str,
        default="BUS-001",
        help="Identifier for Bus Simulator 1 (default: BUS-001).",
    )
    parser.add_argument(
        "--bus2-id",
        type=str,
        default="BUS-002",
        help="Identifier for Bus Simulator 2 (default: BUS-002).",
    )
    parser.add_argument(
        "--bus1-port",
        type=int,
        default=8001,
        help="Port for Bus 1 demonstration UI (default: 8001).",
    )
    parser.add_argument(
        "--bus2-port",
        type=int,
        default=8002,
        help="Port for Bus 2 demonstration UI (default: 8002).",
    )
    parser.add_argument(
        "--route",
        type=str,
        default="ROUTE-PUNE-FC",
        help="Pune road corridor for both buses (default: ROUTE-PUNE-FC).",
    )
    parser.add_argument(
        "--stagger-seconds",
        type=float,
        default=6.0,
        help="Delay in seconds before dispatching Bus 2 to support fleet fusion (default: 6.0).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically launch the browser dashboard.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run bus simulators in headless pipeline mode without local simulator web UIs.",
    )
    parser.add_argument(
        "--video",
        type=str,
        default="data/videos/road_video.mp4",
        help="Input video file or 'real' for edge model detection (default: data/videos/road_video.mp4).",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="models/best.pt",
        help="Path to trained YOLO model weights (default: models/best.pt).",
    )
    return parser.parse_args()


class ServiceManager:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.processes: dict[str, Popen] = {}
        self.shutdown_event = threading.Event()
        self.log_threads: list[threading.Thread] = []

    def _stream_output(self, name: str, color: str, pipe: PIPE) -> None:
        """Stream subprocess stdout/stderr line-by-line with service prefix."""
        try:
            for line in iter(pipe.readline, b""):
                if self.shutdown_event.is_set():
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if decoded:
                    print(f"{color}[{name}]{Colors.RESET} {decoded}", flush=True)
        except Exception:
            pass
        finally:
            pipe.close()

    def start_process(self, name: str, color: str, cmd: list[str]) -> Popen:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONPATH"] = str(REPO_ROOT)

        proc = Popen(
            cmd,
            stdout=PIPE,
            stderr=PIPE,
            cwd=str(REPO_ROOT),
            env=env,
        )
        self.processes[name] = proc

        t_out = threading.Thread(
            target=self._stream_output,
            args=(name, color, proc.stdout),
            daemon=True,
        )
        t_err = threading.Thread(
            target=self._stream_output,
            args=(f"{name}:ERR", Colors.RED, proc.stderr),
            daemon=True,
        )
        t_out.start()
        t_err.start()
        self.log_threads.extend([t_out, t_err])
        return proc

    def wait_for_backend_health(self, timeout_sec: float = 15.0) -> bool:
        url = f"http://{self.args.backend_host}:{self.args.backend_port}/health"
        deadline = time.time() + timeout_sec
        print(f"{Colors.BLUE}[RUNNER]{Colors.RESET} Waiting for backend health at {url}...", flush=True)

        while time.time() < deadline:
            if self.shutdown_event.is_set():
                return False
            backend_proc = self.processes.get("BACKEND")
            if backend_proc and backend_proc.poll() is not None:
                print(f"{Colors.RED}[RUNNER] Backend process terminated prematurely with code {backend_proc.returncode}{Colors.RESET}", flush=True)
                return False
            try:
                with urllib.request.urlopen(url, timeout=1.0) as resp:
                    if resp.status == 200:
                        print(f"{Colors.GREEN}[RUNNER] Backend is healthy and ready.{Colors.RESET}", flush=True)
                        return True
            except Exception:
                time.sleep(0.4)

        print(f"{Colors.RED}[RUNNER] Backend failed to become healthy within {timeout_sec}s.{Colors.RESET}", flush=True)
        return False

    def run(self) -> int:
        print_banner()

        # Step 1: Start Backend
        print(f"{Colors.BLUE}[RUNNER]{Colors.RESET} Starting FastAPI Backend on port {self.args.backend_port}...", flush=True)
        backend_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            self.args.backend_host,
            "--port",
            str(self.args.backend_port),
            "--log-level",
            "warning",
        ]
        self.start_process("BACKEND", Colors.GREEN, backend_cmd)

        if not self.wait_for_backend_health():
            self.stop_all()
            return 1

        backend_url = f"http://{self.args.backend_host}:{self.args.backend_port}"

        # Step 2: Start Actual Bus Simulator 1 (BUS-001)
        print(
            f"{Colors.BLUE}[RUNNER]{Colors.RESET} Starting Bus 1 ({self.args.bus1_id}) on corridor '{self.args.route}'...",
            flush=True,
        )
        bus1_cmd = [
            sys.executable,
            "bus-simulator/main.py",
            "--bus-id",
            self.args.bus1_id,
            "--route",
            self.args.route,
            "--port",
            str(self.args.bus1_port),
            "--host",
            self.args.backend_host,
            "--backend-url",
            backend_url,
            "--start-seq",
            "10001",
            "--video",
            self.args.video,
            "--weights",
            self.args.weights,
        ]
        if self.args.headless:
            bus1_cmd.append("--headless")
        self.start_process(self.args.bus1_id, Colors.CYAN, bus1_cmd)

        # Step 3: Stagger Delay for Fleet Fusion
        stagger = max(0.5, self.args.stagger_seconds)
        print(
            f"{Colors.BLUE}[RUNNER]{Colors.RESET} Waiting {stagger:.1f}s before starting {self.args.bus2_id} to establish spatial-temporal fleet fusion conditions...",
            flush=True,
        )
        start_wait = time.time()
        while time.time() - start_wait < stagger:
            if self.shutdown_event.is_set():
                self.stop_all()
                return 0
            time.sleep(0.2)

        # Step 4: Start Actual Bus Simulator 2 (BUS-002)
        print(
            f"{Colors.BLUE}[RUNNER]{Colors.RESET} Starting Bus 2 ({self.args.bus2_id}) on same corridor '{self.args.route}'...",
            flush=True,
        )
        bus2_video = self.args.video
        bus2_cmd = [
            sys.executable,
            "bus-simulator/main.py",
            "--bus-id",
            self.args.bus2_id,
            "--route",
            self.args.route,
            "--port",
            str(self.args.bus2_port),
            "--host",
            self.args.backend_host,
            "--backend-url",
            backend_url,
            "--start-seq",
            "20001",
            "--video",
            bus2_video,
            "--weights",
            self.args.weights,
        ]
        if self.args.headless:
            bus2_cmd.append("--headless")
        self.start_process(self.args.bus2_id, Colors.YELLOW, bus2_cmd)

        # Print system endpoints
        dashboard_url = f"{backend_url}/dashboard"
        print(
            f"""
{Colors.GREEN}{Colors.BOLD}================================================================================
  ALL SERVICES ACTIVE AND STREAMING
================================================================================{Colors.RESET}
  * GIS Live Dashboard:   {dashboard_url}
  * Backend API Docs:     {backend_url}/docs
  * Bus 1 Telemetry UI:   http://{self.args.backend_host}:{self.args.bus1_port} ({self.args.bus1_id})
  * Bus 2 Telemetry UI:   http://{self.args.backend_host}:{self.args.bus2_port} ({self.args.bus2_id})
  * Corridor:             {self.args.route}
  * Fleet Fusion Engine:  Active (Multi-bus cross-confirmation)
{Colors.GREEN}================================================================================{Colors.RESET}
  Press Ctrl+C to terminate all services cleanly.
""",
            flush=True,
        )

        # Step 5: Open Browser Dashboard
        if not self.args.no_browser:
            def _open_browser() -> None:
                time.sleep(1.5)
                try:
                    webbrowser.open(dashboard_url)
                except Exception:
                    pass

            threading.Thread(target=_open_browser, daemon=True).start()

        # Step 6: Monitor loop until interrupted
        try:
            while not self.shutdown_event.is_set():
                # Check if any child process died unexpectedly
                for name, proc in list(self.processes.items()):
                    ret = proc.poll()
                    if ret is not None:
                        print(
                            f"{Colors.RED}[RUNNER] Service '{name}' exited unexpectedly with status {ret}.{Colors.RESET}",
                            flush=True,
                        )
                        self.stop_all()
                        return ret or 1
                time.sleep(0.5)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[RUNNER] KeyboardInterrupt received. Initiating graceful shutdown...{Colors.RESET}", flush=True)
            self.stop_all()

        return 0

    def stop_all(self) -> None:
        self.shutdown_event.set()
        print(f"{Colors.BLUE}[RUNNER] Stopping all services...{Colors.RESET}", flush=True)

        for name, proc in list(self.processes.items()):
            if proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

        # Wait up to 3 seconds for graceful exit
        deadline = time.time() + 3.0
        for name, proc in list(self.processes.items()):
            remaining = max(0.1, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        print(f"{Colors.GREEN}[RUNNER] All services stopped cleanly.{Colors.RESET}", flush=True)


def main() -> None:
    args = parse_args()
    manager = ServiceManager(args)

    def handle_signal(sig: int, frame: object) -> None:
        print(f"\n{Colors.YELLOW}[RUNNER] Caught signal {sig}. Exiting...{Colors.RESET}", flush=True)
        manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    exit_code = manager.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
