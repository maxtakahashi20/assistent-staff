"""Polling coordinator for an authorized source adapter."""

from __future__ import annotations

import logging
from PySide6.QtCore import QObject, QTimer, Signal

from config.settings import Settings
from core.queue_manager import QueueManager
from integrations.discord_authorized import (
    AuthorizedQueueSource,
    JsonFileFeedSource,
    ManualOnlySource,
    SourceUnavailable,
)

logger = logging.getLogger(__name__)


class QueueMonitor(QObject):
    status_changed = Signal(str, str)  # status text, status code
    snapshot_updated = Signal(object, object)  # active entries, channel id
    new_players_detected = Signal(object)

    def __init__(self, queue_manager: QueueManager, settings: Settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.queue_manager = queue_manager
        self.settings = settings
        self.source: AuthorizedQueueSource = self._build_source(settings)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_once)
        self.timer.setInterval(settings.refresh_interval_seconds * 1000)
        self._last_channel_id: str | None = None
        self._last_error: str | None = None

    @staticmethod
    def _build_source(settings: Settings) -> AuthorizedQueueSource:
        if settings.source_mode == "json_file" and settings.feed_path.strip():
            return JsonFileFeedSource(settings.feed_path)
        return ManualOnlySource()

    def start(self) -> None:
        if not self.timer.isActive():
            self.timer.start()
        self.poll_once()

    def stop(self) -> None:
        self.timer.stop()

    def reconfigure(self, settings: Settings) -> None:
        self.settings = settings
        self.source = self._build_source(settings)
        self.timer.setInterval(settings.refresh_interval_seconds * 1000)
        self._last_error = None
        self._last_channel_id = None
        self.poll_once()

    def poll_once(self) -> None:
        if isinstance(self.source, ManualOnlySource):
            self.status_changed.emit("Modo manual — sem fonte Discord conectada", "manual")
            self.snapshot_updated.emit(self.queue_manager.list_active(), None)
            return
        try:
            snapshot = self.source.poll()
            if snapshot is not None:
                new_entries = self.queue_manager.sync_snapshot(snapshot)
                self._last_channel_id = snapshot.helper_voice_channel_id
                if new_entries:
                    self.new_players_detected.emit(new_entries)
                self.snapshot_updated.emit(
                    self.queue_manager.list_active(), snapshot.helper_voice_channel_id
                )
            self.status_changed.emit("Feed autorizado ativo", "connected")
            self._last_error = None
        except SourceUnavailable as exc:
            message = str(exc)
            if message != self._last_error:
                logger.warning("Fonte de fila indisponível: %s", message)
            self._last_error = message
            self.status_changed.emit(f"Feed indisponível — {message}", "error")
        except Exception:
            logger.exception("Erro inesperado ao consultar fonte autorizada")
            self.status_changed.emit("Erro ao consultar o feed autorizado", "error")
