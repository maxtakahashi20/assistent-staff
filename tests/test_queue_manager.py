"""Regression tests for queue state transitions and snapshot reconciliation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.queue_manager import QueueManager
from database.connection import Database
from database.models import QueuePerson, QueueSnapshot


class QueueManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test.sqlite3")
        self.manager = QueueManager(self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_snapshot_adds_new_player_only_once(self) -> None:
        snapshot = QueueSnapshot((QueuePerson("Player_1", "123"),))
        first = self.manager.sync_snapshot(snapshot)
        second = self.manager.sync_snapshot(snapshot)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 0)
        self.assertEqual(len(self.manager.list_active()), 1)

    def test_absent_authorized_player_is_marked_as_left(self) -> None:
        self.manager.sync_snapshot(QueueSnapshot((QueuePerson("Player_1", "123"),)))
        self.manager.sync_snapshot(QueueSnapshot(tuple()))
        history = self.manager.list_history()
        self.assertEqual(history[0].status, "left")

    def test_manual_entry_is_not_closed_by_external_snapshot(self) -> None:
        self.manager.add_manual("Manual_Player")
        self.manager.sync_snapshot(QueueSnapshot(tuple()))
        self.assertEqual(self.manager.list_active()[0].status, "waiting")

    def test_start_and_complete_transition(self) -> None:
        entry = self.manager.add_manual("Player_2")
        self.manager.mark_started(entry.id)
        self.assertEqual(self.manager.get_entry(entry.id).status, "in_progress")
        self.manager.mark_completed(entry.id)
        self.assertEqual(self.manager.get_entry(entry.id).status, "completed")

    def test_duplicate_manual_name_is_rejected(self) -> None:
        self.manager.add_manual("Player_3")
        with self.assertRaises(ValueError):
            self.manager.add_manual("  player_3  ")


if __name__ == "__main__":
    unittest.main()
