"""City Support Assistant entry point."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from config.settings import Settings
from core.logging_config import configure_logging
from core.queue_manager import QueueManager
from database.connection import Database
from ui.main_window import MainWindow

APP_NAME = "City Support Assistant"


def get_data_directory() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "CitySupportAssistant"
    return Path.home() / ".local" / "share" / "city-support-assistant"


def main() -> int:
    data_dir = get_data_directory()
    configure_logging(data_dir)
    logger = logging.getLogger(__name__)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("CitySupportAssistant")
    app.setQuitOnLastWindowClosed(True)

    try:
        database = Database(data_dir / "city-support.sqlite3")
        settings = Settings.load(database)
        manager = QueueManager(database)
        window = MainWindow(database, manager, settings)
        window.show()
        logger.info("Aplicativo iniciado. Base local: %s", data_dir)
        return app.exec()
    except Exception as exc:
        logger.exception("Falha ao iniciar o aplicativo")
        QMessageBox.critical(None, "Falha ao iniciar", f"Não foi possível iniciar o aplicativo:\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
