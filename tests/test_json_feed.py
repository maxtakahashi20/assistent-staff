"""Tests for the authorized JSON file adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from integrations.discord_authorized import JsonFileFeedSource, SourceUnavailable


class JsonFeedTests(unittest.TestCase):
    def test_reads_queue_and_helper_channel(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "feed.json"
            path.write_text(json.dumps({
                "generated_at": "2026-11-06T03:30:00Z",
                "helper_voice_channel_id": "987654321",
                "queue": [{
                    "user_id": "123456789",
                    "display_name": "Player_X",
                    "joined_at": "2026-11-06T03:25:00Z",
                }],
            }), encoding="utf-8")
            source = JsonFileFeedSource(path)
            snapshot = source.poll()
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.helper_voice_channel_id, "987654321")
            self.assertEqual(snapshot.people[0].display_name, "Player_X")
            self.assertIsNone(source.poll(), "Unchanged file should not be reprocessed")

    def test_missing_file_reports_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = JsonFileFeedSource(Path(folder) / "missing.json")
            with self.assertRaises(SourceUnavailable):
                source.poll()


if __name__ == "__main__":
    unittest.main()
