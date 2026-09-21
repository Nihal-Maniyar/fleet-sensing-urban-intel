"""Tests for SQLite WAL store-and-forward outbox queue."""

import os
import tempfile
import unittest
from pathlib import Path
import sys

sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from events.schema import Event
from transport.outbox import SQLiteOutbox


class TestSQLiteOutbox(unittest.TestCase):
    """Verify offline outbox queueing, WAL journaling, and idempotent replay."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_outbox.db")
        self.outbox = SQLiteOutbox(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_wal_mode_enabled(self):
        with self.outbox._connection() as conn:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

    def test_enqueue_and_get_pending(self):
        event = Event(
            event_id="EVT-000001",
            bus_id="BUS-001",
            event_type="POTHOLE",
            timestamp="2026-09-20T10:30:00Z",
            latitude=18.5204,
            longitude=73.8567,
            confidence=0.91,
            evidence_image="runtime/evidence/EVT-000001.jpg",
            source="actual_bus_simulator",
            connectivity_state="OFFLINE",
        )
        # First enqueue
        inserted = self.outbox.enqueue(event)
        self.assertTrue(inserted)
        self.assertEqual(self.outbox.count_pending(), 1)

        # Idempotency: enqueue same event again -> must ignore duplicate
        inserted_again = self.outbox.enqueue(event)
        self.assertFalse(inserted_again)
        self.assertEqual(self.outbox.count_pending(), 1)

        # Retrieve pending
        pending = self.outbox.get_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].event_id, "EVT-000001")

        # Mark replayed
        self.outbox.mark_replayed("EVT-000001")
        self.assertEqual(self.outbox.count_pending(), 0)
        self.assertEqual(self.outbox.count_total(), 1)


if __name__ == "__main__":
    unittest.main()
