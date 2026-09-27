"""SQLite Write-Ahead Logging (WAL) store-and-forward outbox buffer.

Guarantees crash resilience and idempotent offline queueing on the edge bus device.
Complies with docs/api-contract.md and docs/data-flow.md.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

try:
    from events.schema import Event
except ImportError:
    from ..events.schema import Event

logger = logging.getLogger("actual_bus_simulator.transport.outbox")


class SQLiteOutbox:
    """Persistent SQLite store-and-forward buffer using Write-Ahead Logging (WAL)."""

    def __init__(self, db_path: str = "runtime/edge_outbox.db") -> None:
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            # Enforce Write-Ahead Logging for concurrency and durability
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize the outbox schema and indices."""
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_outbox (
                    event_id TEXT PRIMARY KEY,
                    bus_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    replayed_at TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_edge_outbox_status
                ON edge_outbox (status);
                """
            )

    def enqueue(self, event: Event) -> bool:
        """Store an event into the offline outbox queue.

        Uses INSERT OR IGNORE to guarantee idempotency.
        """
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO edge_outbox (
                    event_id, bus_id, event_type, timestamp, payload,
                    status, retry_count, created_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING', 0, ?);
                """,
                (
                    event.event_id,
                    event.bus_id,
                    event.event_type,
                    event.timestamp,
                    event.to_json(),
                    now_utc,
                ),
            )
            inserted = cursor.rowcount > 0
            if inserted:
                logger.info("Enqueued event %s to SQLite WAL outbox (%s)", event.event_id, self.db_path)
            return inserted

    def get_pending(self) -> List[Event]:
        """Retrieve all pending events ordered chronologically."""
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM edge_outbox
                WHERE status = 'PENDING'
                ORDER BY timestamp ASC;
                """
            ).fetchall()
            return [Event.from_json(row["payload"]) for row in rows]

    def mark_replayed(self, event_id: str) -> None:
        """Mark an outbox event as successfully replayed."""
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE edge_outbox
                SET status = 'REPLAYED',
                    replayed_at = ?
                WHERE event_id = ?;
                """,
                (now_utc, event_id),
            )
            logger.info("Marked event %s as REPLAYED in outbox", event_id)

    def count_pending(self) -> int:
        """Count pending events in outbox."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM edge_outbox WHERE status = 'PENDING';"
            ).fetchone()
            return int(row["cnt"]) if row else 0

    def count_total(self) -> int:
        """Count total events in outbox."""
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM edge_outbox;").fetchone()
            return int(row["cnt"]) if row else 0

    def clear(self) -> None:
        """Clear all entries (useful in testing)."""
        with self._connection() as conn:
            conn.execute("DELETE FROM edge_outbox;")
