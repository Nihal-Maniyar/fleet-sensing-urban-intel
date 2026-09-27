"""Tests verifying SQLite Write-Ahead Logging (WAL) outbox queueing and idempotent replay."""

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent.parent
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

from events.schema import Event
from events.storage import SQLiteOutbox


class TestSQLiteWALOutbox(unittest.TestCase):
    """Verifies edge outbox storage, WAL mode, idempotency, and replay."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_outbox.db")
        self.outbox = SQLiteOutbox(db_path=self.db_path)

        self.sample_event = Event(
            event_id="EVT-000099",
            bus_id="BUS-001",
            event_type="POTHOLE",
            timestamp="2026-09-20T10:00:00Z",
            latitude=18.5204,
            longitude=73.8567,
            road_aligned_latitude=18.5203,
            road_aligned_longitude=73.8568,
            confidence=0.91,
            severity="HIGH",
            evidence_image="runtime/evidence/EVT-000099.jpg",
            source="data_demo_simulator",
            connectivity_state="OFFLINE",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_wal_journal_mode_activated(self) -> None:
        """Confirms SQLite connection uses Write-Ahead Logging (WAL) mode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(mode.lower(), "wal")

    def test_enqueue_and_retrieve_pending(self) -> None:
        """Enqueued event is retrieved in pending state."""
        inserted = self.outbox.enqueue(self.sample_event)
        self.assertTrue(inserted)
        self.assertEqual(self.outbox.count_pending(), 1)

        pending = self.outbox.get_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].event_id, "EVT-000099")
        self.assertEqual(pending[0].bus_id, "BUS-001")
        self.assertEqual(pending[0].connectivity_state, "OFFLINE")

    def test_idempotent_enqueue(self) -> None:
        """Re-inserting the same event_id is silently ignored (idempotent)."""
        inserted_first = self.outbox.enqueue(self.sample_event)
        inserted_second = self.outbox.enqueue(self.sample_event)

        self.assertTrue(inserted_first)
        self.assertFalse(inserted_second)
        self.assertEqual(self.outbox.count_total(), 1)

    def test_mark_replayed(self) -> None:
        """Replaying an event marks its status to REPLAYED and removes from pending."""
        self.outbox.enqueue(self.sample_event)
        self.assertEqual(self.outbox.count_pending(), 1)

        self.outbox.mark_replayed(self.sample_event.event_id)
        self.assertEqual(self.outbox.count_pending(), 0)
        self.assertEqual(self.outbox.count_total(), 1)

        # Inspect database record directly
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT status, replayed_at FROM edge_outbox WHERE event_id = ?",
            (self.sample_event.event_id,),
        ).fetchone()
        conn.close()

        self.assertEqual(row["status"], "REPLAYED")
        self.assertIsNotNone(row["replayed_at"])


if __name__ == "__main__":
    unittest.main()
