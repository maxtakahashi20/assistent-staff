"""Authorized, read-only queue source adapters.

This module deliberately does not authenticate as a human Discord user, read
Discord desktop session files, inspect browser storage, or call private APIs.
The JSON adapter consumes a local file produced by a server-approved
integration (for example, an administrator-operated bot or backend service).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Protocol

from database.models import QueuePerson, QueueSnapshot

logger = logging.getLogger(__name__)


class SourceUnavailable(RuntimeError):
    """Raised when the configured authorized source cannot be read."""


class AuthorizedQueueSource(Protocol):
    def poll(self) -> QueueSnapshot | None:
        """Return a snapshot, or None when no new snapshot is available."""


class ManualOnlySource:
    """No external source; queue data is entered by the staff member."""

    def poll(self) -> None:
        return None


class JsonFileFeedSource:
    """Reads snapshots from a JSON file created by an authorized service."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path).expanduser()
        self._last_signature: tuple[int, int] | None = None

    def poll(self) -> QueueSnapshot | None:
        if not self.file_path.exists():
            raise SourceUnavailable(f"Feed não encontrado: {self.file_path}")

        try:
            stat = self.file_path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
            if signature == self._last_signature:
                return None
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceUnavailable(f"Não foi possível ler o feed: {exc}") from exc

        if not isinstance(raw, dict):
            raise SourceUnavailable("O feed precisa ser um objeto JSON.")
        queue_raw = raw.get("queue", [])
        if not isinstance(queue_raw, list):
            raise SourceUnavailable("O campo 'queue' precisa ser uma lista.")

        people: list[QueuePerson] = []
        for index, item in enumerate(queue_raw):
            if not isinstance(item, dict):
                logger.warning("Item %s ignorado: formato inválido", index)
                continue
            name = str(item.get("display_name", "")).strip()
            if not name:
                logger.warning("Item %s ignorado: display_name ausente", index)
                continue
            user_id = item.get("user_id")
            joined_at = item.get("joined_at")
            people.append(
                QueuePerson(
                    display_name=name,
                    discord_user_id=str(user_id) if user_id else None,
                    joined_at=str(joined_at) if joined_at else None,
                )
            )

        helper_channel = raw.get("helper_voice_channel_id")
        generated_at = raw.get("generated_at")
        self._last_signature = signature
        return QueueSnapshot(
            people=tuple(people),
            helper_voice_channel_id=(str(helper_channel) if helper_channel else None),
            generated_at=(str(generated_at) if generated_at else None),
        )
