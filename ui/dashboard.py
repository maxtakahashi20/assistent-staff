from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QMessageBox,
)

from core.queue_manager import QueueManager
from database.models import QueueEntry
from ui.components.queue_table import QueueTable
from ui.components.stat_card import StatCard


class DashboardPage(QWidget):
    def __init__(self, manager: QueueManager, on_open_queue, on_demo_data) -> None:
        super().__init__()
        self.manager = manager
        self.on_open_queue = on_open_queue
        self.on_demo_data = on_demo_data
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(18)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Visão geral")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Acompanhe a fila e organize seus atendimentos.")
        subtitle.setObjectName("Muted")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()
        self.demo_button = QPushButton("＋  Carregar dados de demonstração")
        self.demo_button.clicked.connect(self._load_demo)
        header.addWidget(self.demo_button)
        root.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.waiting_card = StatCard("Aguardando", "0", "#e6b65c")
        self.active_card = StatCard("Em atendimento", "0", "#7c9bff")
        self.completed_card = StatCard("Concluídos hoje", "0", "#58c99b")
        self.avg_card = StatCard("Espera média hoje", "—", "#b39aff")
        for card in (self.waiting_card, self.active_card, self.completed_card, self.avg_card):
            cards.addWidget(card)
        root.addLayout(cards)

        info_row = QHBoxLayout()
        info_row.setSpacing(14)
        self.monitor_panel = self._info_panel("MONITORAMENTO", "Modo manual", "Sem integração Discord conectada")
        self.channel_panel = self._info_panel("SUA CANALETA", "Não identificada", "Disponível via feed autorizado")
        info_row.addWidget(self.monitor_panel, 1)
        info_row.addWidget(self.channel_panel, 1)
        root.addLayout(info_row)

        queue_header = QHBoxLayout()
        section_title = QLabel("Fila atual")
        section_title.setObjectName("SectionTitle")
        queue_header.addWidget(section_title)
        queue_header.addStretch()
        open_button = QPushButton("Ver fila completa  →")
        open_button.clicked.connect(self.on_open_queue)
        queue_header.addWidget(open_button)
        root.addLayout(queue_header)

        self.table = QueueTable(selectable=False)
        self.table.setMaximumHeight(300)
        root.addWidget(self.table)
        root.addStretch(1)
        self.refresh()

    def _info_panel(self, eyebrow: str, value: str, detail: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        eyebrow_label = QLabel(eyebrow)
        eyebrow_label.setObjectName("MetricLabel")
        value_label = QLabel(value)
        value_label.setObjectName("SectionTitle")
        detail_label = QLabel(detail)
        detail_label.setObjectName("Muted")
        detail_label.setWordWrap(True)
        layout.addWidget(eyebrow_label)
        layout.addWidget(value_label)
        layout.addWidget(detail_label)
        panel.value_label = value_label  # type: ignore[attr-defined]
        panel.detail_label = detail_label  # type: ignore[attr-defined]
        return panel

    def set_monitor_status(self, text: str, code: str) -> None:
        self.monitor_panel.value_label.setText(  # type: ignore[attr-defined]
            {"connected": "Feed autorizado ativo", "manual": "Modo manual", "error": "Feed indisponível"}.get(code, text)
        )
        self.monitor_panel.detail_label.setText(text)  # type: ignore[attr-defined]

    def set_helper_channel(self, channel_id: str | None, channel_name: str) -> None:
        value = channel_name if channel_name else "Não identificada"
        self.channel_panel.value_label.setText(value)  # type: ignore[attr-defined]
        self.channel_panel.detail_label.setText(
            f"ID: {channel_id}" if channel_id else "Disponível via feed autorizado"
        )  # type: ignore[attr-defined]

    def refresh(self) -> None:
        entries = self.manager.list_active()
        waiting = sum(entry.status == "waiting" for entry in entries)
        in_progress = sum(entry.status == "in_progress" for entry in entries)
        self.waiting_card.set_value(str(waiting))
        self.active_card.set_value(str(in_progress))
        self.completed_card.set_value(str(self.manager.count_today_completed()))
        avg = self.manager.average_wait_seconds_today()
        self.avg_card.set_value(_format_seconds(avg) if avg else "—")
        self.table.populate(entries[:8])

    def _load_demo(self) -> None:
        count = self.manager.load_demo_data()
        self.refresh()
        QMessageBox.information(
            self,
            "Dados de demonstração",
            f"{count} registro(s) fictício(s) adicionado(s).\n\nEles estão identificados como 'Demonstração' e não representam dados reais do Discord.",
        )


def _format_seconds(seconds: int) -> str:
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}min" if hours else f"{minutes}min"
