"""SQLite WAL store-and-forward outbox queue for edge offline buffering and replay.

Complies strictly with the requirement that offline edge events are queued in
SQLite/WAL and later published with unmodified event_id values for idempotent ingestion.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

from .schema import Event


class SQLiteOutbox:
    """Persistent SQLite store-and-forward buffer using Write-Ahead Logging (WAL)."""

    def __init__(self, db_path: str = "runtime/edge_outbox.db") -> None:
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Enforce Write-Ahead Logging for high concurrency and crash resilience
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize the edge_outbox schema."""
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
        """Store an event in the offline outbox queue.

        Uses INSERT OR IGNORE to guarantee idempotency.

        Returns:
            True if newly inserted, False if already present.
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
            return cursor.rowcount > 0

    def get_pending(self) -> List[Event]:
        """Retrieve all queued events waiting for replay, ordered chronologically."""
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

    def increment_retry(self, event_id: str) -> None:
        """Increment retry attempt counter for an event."""
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE edge_outbox
                SET retry_count = retry_count + 1
                WHERE event_id = ?;
                """,
                (event_id,),
            )

    def count_pending(self) -> int:
        """Count pending queued events."""
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
