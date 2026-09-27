#!/usr/bin/env python3
"""Compatibility wrapper for the repository's demo runner.

This keeps the CI entrypoint (`python scripts/run_demo.py --delay 0.0`)
working even though the actual end-to-end runner now lives in `run_project.py`.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compatibility wrapper for the Fleet Sensing demo runner.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Alias for the end-to-end runner delay/stagger value in seconds.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run bus simulators in headless mode.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open the browser dashboard.",
    )
    parsed, remaining = parser.parse_known_args(argv)

    # `run_project.py` expects `--stagger-seconds`, not `--delay`.
    if "--stagger-seconds" not in remaining:
        remaining.extend(["--stagger-seconds", str(parsed.delay)])

    if parsed.headless and "--headless" not in remaining:
        remaining.append("--headless")

    if parsed.no_browser and "--no-browser" not in remaining:
        remaining.append("--no-browser")

    # Preserve the repository root on PYTHONPATH when launched via the scripts directory.
    project_root = __file__.resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    sys.argv = [sys.argv[0], *remaining]

    from run_project import main as project_main

    project_main()


if __name__ == "__main__":
    main()
