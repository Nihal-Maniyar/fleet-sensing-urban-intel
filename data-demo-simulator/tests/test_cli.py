"""Tests for CLI arguments and file emission modes."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent.parent
MAIN_PY = os.path.join(str(SIM_DIR), "main.py")


class TestCLI(unittest.TestCase):
    """Test CLI behavior, flags, and outputs."""

    def test_cli_list_scenarios(self) -> None:
        """--list-scenarios prints available scenarios."""
        result = subprocess.run(
            [sys.executable, MAIN_PY, "--list-scenarios"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("dual_bus_pothole", result.stdout)
        self.assertIn("connectivity_outage", result.stdout)
        self.assertIn("diverse_events", result.stdout)
        self.assertIn("resolution_verification", result.stdout)
        self.assertIn("master_demo", result.stdout)

    def test_cli_stdout_ndjson(self) -> None:
        """--mode ndjson produces valid newline-delimited JSON."""
        result = subprocess.run(
            [sys.executable, MAIN_PY, "--scenario", "dual_bus_pothole", "--mode", "ndjson", "--no-evidence"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("event_id", parsed)
            self.assertIn("bus_id", parsed)

    def test_cli_file_output(self) -> None:
        """--mode file writes events to target file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "events.ndjson")
            result = subprocess.run(
                [
                    sys.executable,
                    MAIN_PY,
                    "--scenario",
                    "diverse_events",
                    "--mode",
                    "file",
                    "--output-file",
                    out_file,
                    "--no-evidence",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            self.assertEqual(len(lines), 4)


if __name__ == "__main__":
    unittest.main()
