from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QStackedWidget, QStatusBar, QSystemTrayIcon, QMenu,
    QApplication, QStyle,
)

from config.settings import Settings
from core.monitor import QueueMonitor
from core.notifications import NotificationService
from core.queue_manager import QueueManager
from database.connection import Database
from database.models import QueueEntry
from ui.dashboard import DashboardPage
from ui.history_view import HistoryPage
from ui.queue_view import QueuePage
from ui.settings_view import SettingsPage
from ui.theme import DARK_QSS, LIGHT_QSS

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, db: Database, manager: QueueManager, settings: Settings) -> None:
        super().__init__()
        self.db = db
        self.manager = manager
        self.settings = settings
        self.setWindowTitle("City Support Assistant")
        self.setMinimumSize(1020, 680)
        self.resize(1280, 820)
        self._setup_tray()
        self.notifications = NotificationService(self.tray)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.topbar = self._build_topbar()
        content_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage(manager, lambda: self.navigate(1), self._load_demo)
        self.queue_page = QueuePage(manager)
        self.history_page = HistoryPage(manager)
        self.settings_page = SettingsPage(db, settings, self.apply_settings)
        for page in (self.dashboard, self.queue_page, self.history_page, self.settings_page):
            self.stack.addWidget(page)
        content_layout.addWidget(self.stack, 1)
        layout.addWidget(content, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Aplicativo local pronto")
        self.setStyleSheet(DARK_QSS if settings.theme == "dark" else LIGHT_QSS)

        self.monitor = QueueMonitor(manager, settings, self)
        self.monitor.status_changed.connect(self._on_monitor_status)
        self.monitor.snapshot_updated.connect(self._on_snapshot)
        self.monitor.new_players_detected.connect(self._on_new_players)
        self.monitor.start()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_views)
        self.refresh_timer.start(1000)
        self.navigate(0)

    def _setup_tray(self) -> None:
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "app.svg"
        icon = QIcon(str(icon_path)) if icon_path.exists() else self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("City Support Assistant")
        menu = QMenu()
        show_action = QAction("Abrir painel", self)
        show_action.triggered.connect(self.showNormal)
        exit_action = QAction("Encerrar", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(224)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 20, 14, 16)
        layout.setSpacing(8)
        brand = QLabel("◈  CITY SUPPORT")
        brand.setObjectName("Brand")
        layout.addWidget(brand)
        version = QLabel("STAFF WORKSPACE  ·  v1.0")
        version.setObjectName("Muted")
        version.setStyleSheet("font-size: 8pt; letter-spacing: 1px;")
        layout.addWidget(version)
        layout.addSpacing(28)

        self.nav_buttons: list[QPushButton] = []
        nav_items = [("▦   Visão geral", 0), ("☷   Fila de atendimento", 1), ("◷   Histórico", 2), ("⚙   Configurações", 3)]
        for label, index in nav_items:
            button = QPushButton(label)
            button.setObjectName("Nav")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            layout.addWidget(button)
            self.nav_buttons.append(button)
        layout.addStretch()
        disclaimer = QLabel("MODO LOCAL\nSem automação de conta pessoal do Discord.")
        disclaimer.setObjectName("Muted")
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("font-size: 8pt; padding: 9px; border: 1px solid #2b3a52; border-radius: 8px;")
        layout.addWidget(disclaimer)
        return sidebar

    def _build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("Topbar")
        topbar.setFixedHeight(66)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(24, 0, 24, 0)
        self.page_heading = QLabel("Visão geral")
        self.page_heading.setObjectName("SectionTitle")
        layout.addWidget(self.page_heading)
        layout.addStretch()
        self.monitor_badge = QLabel("●  MODO MANUAL")
        self.monitor_badge.setStyleSheet("color: #e6b65c; font-weight: 650; padding: 7px 11px; background: rgba(230,182,92,0.10); border-radius: 8px;")
        layout.addWidget(self.monitor_badge)
        return topbar

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for current, button in enumerate(self.nav_buttons):
            button.setChecked(current == index)
        headings = ["Visão geral", "Fila de atendimento", "Histórico", "Configurações"]
        self.page_heading.setText(headings[index])
        self.refresh_views()

    def apply_settings(self, settings: Settings) -> None:
        self.settings = settings
        self.setStyleSheet(DARK_QSS if settings.theme == "dark" else LIGHT_QSS)
        self.monitor.reconfigure(settings)
        self.status.showMessage("Configurações atualizadas", 4000)

    def refresh_views(self) -> None:
        self.dashboard.refresh()
        self.queue_page.refresh()
        self.history_page.refresh()

    def _on_monitor_status(self, text: str, code: str) -> None:
        labels = {"connected": "●  FEED AUTORIZADO", "manual": "●  MODO MANUAL", "error": "●  FEED INDISPONÍVEL"}
        colors = {"connected": "#58c99b", "manual": "#e6b65c", "error": "#f07b83"}
        self.monitor_badge.setText(labels.get(code, "●  MONITORAMENTO"))
        self.monitor_badge.setStyleSheet(
            f"color: {colors.get(code, '#9aa8bf')}; font-weight: 650; padding: 7px 11px; "
            "background: rgba(120,140,180,0.10); border-radius: 8px;"
        )
        self.dashboard.set_monitor_status(text, code)
        self.status.showMessage(text)

    def _on_snapshot(self, entries: object, channel_id: object) -> None:
        channel_text = str(channel_id) if channel_id else None
        channel_name = ""
        if channel_text:
            for name, value in self.settings.work_channels.items():
                if value.strip() and value.strip() == channel_text:
                    channel_name = name
                    break
            if not channel_name:
                channel_name = "Canaleta não mapeada"
        self.dashboard.set_helper_channel(channel_text, channel_name)
        self.refresh_views()

    def _on_new_players(self, entries: object) -> None:
        if not isinstance(entries, list):
            return
        for entry in entries:
            if isinstance(entry, QueueEntry):
                logger.info("Novo jogador detectado: %s (%s)", entry.display_name, entry.source)
                self.notifications.notify_new_player(
                    entry.display_name,
                    desktop_enabled=self.settings.desktop_notifications,
                    sound_enabled=self.settings.sound_enabled,
                    sound_path=self.settings.sound_path,
                )
        self.refresh_views()

    def _load_demo(self) -> None:
        self.manager.load_demo_data()
        self.refresh_views()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API naming
        if self.monitor:
            self.monitor.stop()
        if self.tray:
            self.tray.hide()
        event.accept()
