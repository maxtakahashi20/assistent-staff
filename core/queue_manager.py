"""Queue operations and durable atendimento history."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from database.connection import Database
from database.models import QueueEntry, QueuePerson, QueueSnapshot, utc_now_iso

logger = logging.getLogger(__name__)


class QueueManager:
    ACTIVE_STATUSES = ("waiting", "in_progress")

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_active(self) -> list[QueueEntry]:
        placeholders = ",".join("?" for _ in self.ACTIVE_STATUSES)
        with self.db.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM queue_entries WHERE status IN ({placeholders}) "
                "ORDER BY CASE status WHEN 'in_progress' THEN 0 ELSE 1 END, joined_at ASC",
                self.ACTIVE_STATUSES,
            ).fetchall()
        return [QueueEntry.from_row(row) for row in rows]

    def list_waiting(self) -> list[QueueEntry]:
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM queue_entries WHERE status = 'waiting' ORDER BY joined_at ASC"
            ).fetchall()
        return [QueueEntry.from_row(row) for row in rows]

    def get_entry(self, entry_id: int) -> QueueEntry | None:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT * FROM queue_entries WHERE id = ?", (entry_id,)
            ).fetchone()
        return QueueEntry.from_row(row) if row else None

    def list_history(self, limit: int = 200) -> list[QueueEntry]:
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM queue_entries ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [QueueEntry.from_row(row) for row in rows]

    def sync_snapshot(self, snapshot: QueueSnapshot, source: str = "authorized_feed") -> list[QueueEntry]:
        """Merge an external snapshot; return entries newly detected in queue."""
        now = utc_now_iso()
        added_ids: list[int] = []
        seen_user_ids: set[str] = set()
        seen_names: set[str] = set()

        with self.db.transaction() as connection:
            for person in snapshot.people:
                name_key = _normalize_name(person.display_name)
                seen_names.add(name_key)
                if person.discord_user_id:
                    seen_user_ids.add(person.discord_user_id)
                active = connection.execute(
                    "SELECT id FROM queue_entries WHERE "
                    "((discord_user_id = ?) OR lower(trim(display_name)) = ?) "
                    "AND status IN ('waiting', 'in_progress') ORDER BY id DESC LIMIT 1",
                    (person.discord_user_id or "", name_key),
                ).fetchone()

                if active:
                    continue

                joined_at = _normalize_datetime(person.joined_at) or now
                cursor = connection.execute(
                    """INSERT INTO queue_entries
                       (discord_user_id, display_name, joined_at, status, source,
                        created_at, updated_at)
                       VALUES (?, ?, ?, 'waiting', ?, ?, ?)""",
                    (person.discord_user_id, person.display_name, joined_at, source, now, now),
                )
                entry_id = int(cursor.lastrowid)
                self._add_event(connection, entry_id, "joined", now, f"Origem: {source}")
                added_ids.append(entry_id)

            # Only queued users are auto-closed when absent from a complete snapshot.
            active_waiting = connection.execute(
                "SELECT id, discord_user_id, display_name FROM queue_entries "
                "WHERE status = 'waiting' AND source = ?", (source,)
            ).fetchall()
            for row in active_waiting:
                user_id = row["discord_user_id"]
                key = _normalize_name(str(row["display_name"]))
                # Only records created by this complete feed are reconciled.
                present = (user_id and user_id in seen_user_ids) or key in seen_names
                if not present:
                    connection.execute(
                        "UPDATE queue_entries SET status = 'left', left_at = ?, updated_at = ? WHERE id = ?",
                        (now, now, row["id"]),
                    )
                    self._add_event(connection, int(row["id"]), "left", now, "Saiu da fila")

        return [entry for entry_id in added_ids if (entry := self.get_entry(entry_id))]

    def add_manual(self, display_name: str, discord_user_id: str = "", notes: str = "") -> QueueEntry:
        display_name = display_name.strip()
        if not display_name:
            raise ValueError("Informe o nome do jogador.")
        now = utc_now_iso()
        user_id = discord_user_id.strip() or None
        with self.db.transaction() as connection:
            existing = connection.execute(
                "SELECT id FROM queue_entries WHERE "
                "((discord_user_id = ?) OR lower(trim(display_name)) = ?) "
                "AND status IN ('waiting', 'in_progress') LIMIT 1",
                (user_id or "", _normalize_name(display_name)),
            ).fetchone()
            if existing:
                raise ValueError("Esse jogador já está na fila ou em atendimento.")
            cursor = connection.execute(
                """INSERT INTO queue_entries
                   (discord_user_id, display_name, joined_at, status, source, notes, created_at, updated_at)
                   VALUES (?, ?, ?, 'waiting', 'manual', ?, ?, ?)""",
                (user_id, display_name, now, notes.strip(), now, now),
            )
            entry_id = int(cursor.lastrowid)
            self._add_event(connection, entry_id, "joined", now, "Adicionado manualmente")
        result = self.get_entry(entry_id)
        assert result is not None
        return result

    def load_demo_data(self) -> int:
        """Insert clearly labeled sample records; never represents live Discord data."""
        now = datetime.now(timezone.utc)
        samples = [
            ("Artista_482", "demo-user-001", 7),
            ("Player_Rocha", "demo-user-002", 3),
            ("M4theus", "demo-user-003", 1),
        ]
        inserted = 0
        with self.db.transaction() as connection:
            for name, user_id, minutes in samples:
                existing = connection.execute(
                    "SELECT id FROM queue_entries WHERE discord_user_id = ? "
                    "AND status IN ('waiting', 'in_progress') AND source = 'demo' LIMIT 1",
                    (user_id,),
                ).fetchone()
                if existing:
                    continue
                joined = now.replace(microsecond=0) - timedelta(minutes=minutes)
                joined_iso = joined.isoformat(timespec="seconds")
                current_iso = now.isoformat(timespec="seconds")
                cursor = connection.execute(
                    """INSERT INTO queue_entries
                       (discord_user_id, display_name, joined_at, status, source, notes, created_at, updated_at)
                       VALUES (?, ?, ?, 'waiting', 'demo', 'Dado fictício para demonstração', ?, ?)""",
                    (user_id, name, joined_iso, current_iso, current_iso),
                )
                self._add_event(connection, int(cursor.lastrowid), "joined", current_iso, "Registro de demonstração")
                inserted += 1
        return inserted

    def mark_started(self, entry_id: int) -> None:
        self._change_status(entry_id, "in_progress", "started", "Atendimento iniciado manualmente")

    def mark_completed(self, entry_id: int) -> None:
        self._change_status(entry_id, "completed", "completed", "Atendimento concluído")

    def mark_left(self, entry_id: int) -> None:
        now = utc_now_iso()
        with self.db.transaction() as connection:
            row = connection.execute(
                "SELECT status FROM queue_entries WHERE id = ?", (entry_id,)
            ).fetchone()
            if not row:
                raise ValueError("Registro não encontrado.")
            if row["status"] not in self.ACTIVE_STATUSES:
                raise ValueError("Este registro não está ativo.")
            connection.execute(
                "UPDATE queue_entries SET status='left', left_at=?, updated_at=? WHERE id=?",
                (now, now, entry_id),
            )
            self._add_event(connection, entry_id, "left", now, "Removido manualmente da fila")

    def count_today_completed(self) -> int:
        today = datetime.now().astimezone().date().isoformat()
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM queue_entries WHERE status='completed' "
                "AND substr(updated_at, 1, 10) = ?", (today,)
            ).fetchone()
        return int(row["total"] if row else 0)

    def average_wait_seconds_today(self) -> int:
        """Average queue wait from entry to the manually recorded start event."""
        today = datetime.now().astimezone().date().isoformat()
        with self.db.connect() as connection:
            rows = connection.execute(
                """SELECT q.joined_at, COALESCE(
                       (SELECT e.occurred_at FROM queue_events e
                        WHERE e.entry_id = q.id AND e.event_type = 'started'
                        ORDER BY e.id ASC LIMIT 1), q.updated_at) AS started_at
                   FROM queue_entries q
                   WHERE q.status='completed' AND substr(q.updated_at, 1, 10) = ?""",
                (today,),
            ).fetchall()
        durations: list[float] = []
        for row in rows:
            start = _parse_datetime(row["joined_at"])
            end = _parse_datetime(row["started_at"])
            if start and end and end >= start:
                durations.append((end - start).total_seconds())
        return int(sum(durations) / len(durations)) if durations else 0

    @staticmethod
    def _add_event(connection: sqlite3.Connection, entry_id: int, event_type: str, when: str, details: str) -> None:
        connection.execute(
            "INSERT INTO queue_events(entry_id, event_type, occurred_at, details) VALUES (?, ?, ?, ?)",
            (entry_id, event_type, when, details),
        )

    def _change_status(self, entry_id: int, status: str, event_type: str, details: str) -> None:
        now = utc_now_iso()
        with self.db.transaction() as connection:
            row = connection.execute(
                "SELECT status FROM queue_entries WHERE id = ?", (entry_id,)
            ).fetchone()
            if not row:
                raise ValueError("Registro não encontrado.")
            if row["status"] not in self.ACTIVE_STATUSES:
                raise ValueError("Este registro não está ativo.")
            connection.execute(
                "UPDATE queue_entries SET status=?, updated_at=? WHERE id=?",
                (status, now, entry_id),
            )
            self._add_event(connection, entry_id, event_type, now, details)


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_datetime(value: str | None) -> str | None:
    parsed = _parse_datetime(value)
    return parsed.isoformat(timespec="seconds") if parsed else None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None
