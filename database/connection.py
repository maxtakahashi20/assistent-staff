"""SQLite connection and schema management."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS queue_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_user_id TEXT,
                    display_name TEXT NOT NULL,
                    joined_at TEXT NOT NULL,
                    left_at TEXT,
                    status TEXT NOT NULL CHECK (
                        status IN ('waiting', 'in_progress', 'completed', 'left')
                    ),
                    source TEXT NOT NULL DEFAULT 'manual',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_queue_status_joined
                    ON queue_entries(status, joined_at);
                CREATE INDEX IF NOT EXISTS idx_queue_user_status
                    ON queue_entries(discord_user_id, status);

                CREATE TABLE IF NOT EXISTS queue_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(entry_id) REFERENCES queue_entries(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_events_occurred
                    ON queue_events(occurred_at DESC);
                """
            )

    def get_all_settings(self) -> dict[str, Any]:
        with self.connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        result: dict[str, Any] = {}
        for row in rows:
            try:
                result[row["key"]] = json.loads(row["value"])
            except (TypeError, json.JSONDecodeError):
                result[row["key"]] = row["value"]
        return result

    def save_settings(self, values: dict[str, Any]) -> None:
        with self.transaction() as connection:
            connection.executemany(
                """INSERT INTO settings(key, value) VALUES(?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                [(key, json.dumps(value, ensure_ascii=False)) for key, value in values.items()],
            )
