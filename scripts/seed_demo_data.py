#!/usr/bin/env python3
"""Runner script to seed demonstration data into PostgreSQL/PostGIS database."""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import init_db
from database.seed import seed_database

if __name__ == "__main__":
    print("[Runner] Initializing database schema...")
    init_db()
    print("[Runner] Seeding demo Pune fleet data...")
    seed_database()
    print("[Runner] Seeding completed.")
