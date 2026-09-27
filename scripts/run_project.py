#!/usr/bin/env python3
"""Convenience entrypoint invoking the root master runner (run_project.py)."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run_project import main

if __name__ == "__main__":
    main()
