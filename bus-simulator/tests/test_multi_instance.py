"""Tests for running multiple concurrent bus simulator instances."""

import os
import tempfile
import unittest
from pathlib import Path
import sys

sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from bus_instance import BusInstance


class TestMultiInstance(unittest.TestCase):
    """Verify multiple independent buses can execute concurrently."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_concurrent_bus_instances(self):
        db1 = os.path.join(self.temp_dir.name, "bus_001.db")
        db2 = os.path.join(self.temp_dir.name, "bus_002.db")

        bus1 = BusInstance(
            bus_id="BUS-001",
            route_id="ROUTE-PUNE-FC",
            video_source="synthetic",
            outbox_db=db1,
            initial_connectivity="OFFLINE",
        )

        bus2 = BusInstance(
            bus_id="BUS-002",
            route_id="ROUTE-PUNE-JM",
            video_source="synthetic",
            outbox_db=db2,
            initial_connectivity="ONLINE",
        )

        # Run steps on both instances
        frame1, telem1 = bus1.step()
        frame2, telem2 = bus2.step()

        self.assertEqual(telem1["bus_id"], "BUS-001")
        self.assertEqual(telem1["route_id"], "ROUTE-PUNE-FC")
        self.assertEqual(telem1["connectivity_state"], "OFFLINE")

        self.assertEqual(telem2["bus_id"], "BUS-002")
        self.assertEqual(telem2["route_id"], "ROUTE-PUNE-JM")
        self.assertEqual(telem2["connectivity_state"], "ONLINE")

        # Verify independent outboxes
        self.assertTrue(os.path.exists(db1))
        self.assertTrue(os.path.exists(db2))


if __name__ == "__main__":
    unittest.main()
