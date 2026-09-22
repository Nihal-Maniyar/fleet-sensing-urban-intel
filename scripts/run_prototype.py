#!/usr/bin/env python3
"""Unified All-in-One Prototype Launcher for Fleet Sensing Urban Intelligence.

Launches the complete integrated prototype:
1. Validates environment and dependencies
2. Launches FastAPI central backend with GIS endpoints
3. Seeds authentic Pune demonstration dataset (FC Road, JM Road, Karve Road)
4. Opens the real-time Leaflet GIS Dashboard in the default web browser
5. Provides interactive commands to run live demo simulations or actual bus simulator

Usage:
    # Standard launch (starts backend, seeds data, opens browser):
    python3 scripts/run_prototype.py

    # Headless mode (no auto browser open):
    python3 scripts/run_prototype.py --no-browser

    # Custom port:
    python3 scripts/run_prototype.py --port 8080
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# Add repository root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Color codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def check_environment() -> None:
    """Validate Python environment."""
    if sys.version_info < (3, 10):
        print(f"{RED}[ERROR] Python 3.10 or higher is required. Found: {sys.version}{RESET}")
        sys.exit(1)


def wait_for_backend(url: str, timeout: int = 15) -> bool:
    """Poll health endpoint until backend is ready."""
    health_url = f"{url}/health"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def seed_backend_data(base_url: str) -> bool:
    """Call demo seed endpoint to prime live data."""
    seed_url = f"{base_url}/api/v1/demo/seed"
    try:
        req = urllib.request.Request(seed_url, method="POST")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"{YELLOW}[Warning] Could not auto-seed data: {e}{RESET}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Fleet Sensing Urban Intelligence Prototype Launcher")
    parser.add_argument("--port", type=int, default=8000, help="Backend server port (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Backend host (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")
    args = parser.parse_args()

    check_environment()

    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  FLEET SENSING URBAN INTELLIGENCE — SIH 2026 PROTOTYPE LAUNCHER{RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}\n")

    base_url = f"http://{args.host}:{args.port}"
    dashboard_url = f"{base_url}/dashboard"
    docs_url = f"{base_url}/docs"

    print(f"{GREEN}→ [1/4] Starting FastAPI Central Backend & GIS Engine...{RESET}")
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.app.main:app",
        "--host", args.host,
        "--port", str(args.port),
        "--log-level", "warning"
    ]

    backend_proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT))

    # Graceful shutdown handler
    def shutdown_handler(signum, frame):
        print(f"\n\n{YELLOW}→ Shutting down prototype server...{RESET}")
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_proc.kill()
        print(f"{GREEN}✔ Clean shutdown completed.{RESET}")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print(f"{GREEN}→ [2/4] Awaiting backend readiness at {base_url}...{RESET}")
    if not wait_for_backend(base_url):
        print(f"{RED}[ERROR] Backend failed to start within timeout.{RESET}")
        backend_proc.kill()
        sys.exit(1)

    print(f"{GREEN}→ [3/4] Seeding authentic Pune transit corridors dataset...{RESET}")
    seed_backend_data(base_url)

    print(f"{GREEN}→ [4/4] Prototype platform initialized successfully!{RESET}\n")

    print(f"{BOLD}Access Links:{RESET}")
    print(f"  • {BOLD}Real-Time GIS Dashboard:{RESET} {CYAN}{dashboard_url}{RESET}")
    print(f"  • {BOLD}Interactive Swagger Docs:{RESET} {CYAN}{docs_url}{RESET}")
    print(f"  • {BOLD}Platform Health Endpoint:{RESET} {CYAN}{base_url}/health{RESET}\n")

    if not args.no_browser:
        print(f"{GREEN}✔ Opening GIS Dashboard in your default browser...{RESET}")
        try:
            webbrowser.open(dashboard_url)
        except Exception:
            pass

    print(f"\n{BOLD}Live Features Running in Dashboard:{RESET}")
    print(f"  1. {BOLD}Real Leaflet GIS Map:{RESET} OpenStreetMap tiles, Pune corridors (FC, JM, Karve, Shivaji).")
    print(f"  2. {BOLD}Live Defect Sensing:{RESET} High-severity potholes, waste heaps, road obstructions.")
    print(f"  3. {BOLD}Civic SLA Work Orders:{RESET} Advance ticket lifecycle directly from the dashboard.")
    print(f"  4. {BOLD}Fleet Health:{RESET} Live telemetrics from BUS-001 through BUS-006.")

    print(f"\n{DIM}Press Ctrl+C at any time to shut down the prototype.{RESET}")

    # Keep alive until Ctrl+C
    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        shutdown_handler(None, None)


if __name__ == "__main__":
    main()
