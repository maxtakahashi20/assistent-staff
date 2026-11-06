"""Desktop and sound notifications with graceful cross-platform fallback."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, tray: QSystemTrayIcon | None = None) -> None:
        self.tray = tray

    def notify_new_player(
        self,
        display_name: str,
        desktop_enabled: bool = True,
        sound_enabled: bool = True,
        sound_path: str = "",
    ) -> None:
        if desktop_enabled and self.tray and self.tray.isVisible():
            self.tray.showMessage(
                "Novo jogador aguardando suporte",
                f"{display_name} entrou na fila.",
                QSystemTrayIcon.MessageIcon.Information,
                6000,
            )
        if sound_enabled:
            self.play_sound(sound_path)

    @staticmethod
    def play_sound(sound_path: str = "") -> None:
        path = Path(sound_path).expanduser() if sound_path else None
        if path and path.is_file() and path.suffix.lower() == ".wav":
            try:
                if sys.platform == "win32":
                    import winsound
                    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return
            except (OSError, RuntimeError) as exc:
                logger.warning("Falha ao reproduzir o som configurado: %s", exc)
        app = QApplication.instance()
        if app:
            app.beep()
