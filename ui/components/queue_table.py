from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

from database.models import QueueEntry


class QueueTable(QTableWidget):
    HEADERS = ["JOGADOR", "ENTRADA", "TEMPO DE ESPERA", "STATUS", "ORIGEM"]

    def __init__(self, selectable: bool = True) -> None:
        super().__init__(0, len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
            if selectable else QTableWidget.SelectionMode.NoSelection
        )
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(self.HEADERS)):
            self.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setDefaultSectionSize(42)

    def populate(self, entries: list[QueueEntry]) -> None:
        self.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [
                entry.display_name,
                _format_time(entry.joined_at),
                _format_duration(entry.joined_at),
                _status_label(entry.status),
                _source_label(entry.source),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, entry.id)
                if column == 0:
                    item.setToolTip(entry.discord_user_id or "ID Discord não disponível")
                if column == 3:
                    color = {
                        "waiting": "#e6b65c",
                        "in_progress": "#72a0ff",
                        "completed": "#58c99b",
                        "left": "#8995a8",
                    }.get(entry.status, "#8995a8")
                    item.setForeground(Qt.GlobalColor.white if self.palette().window().color().lightness() < 128 else Qt.GlobalColor.black)
                    item.setData(Qt.ItemDataRole.ToolTipRole, f"Status: {value}")
                    item.setBackground(_qcolor(color))
                self.setItem(row, column, item)

    def selected_entry_id(self) -> int | None:
        row = self.currentRow()
        if row < 0:
            return None
        item = self.item(row, 0)
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        return int(value) if value is not None else None


def _qcolor(value: str):
    from PySide6.QtGui import QColor
    return QColor(value)


def _parse(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _format_time(value: str) -> str:
    return _parse(value).astimezone().strftime("%H:%M:%S")


def _format_duration(value: str) -> str:
    seconds = max(0, int((datetime.now(timezone.utc) - _parse(value).astimezone(timezone.utc)).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _status_label(value: str) -> str:
    return {
        "waiting": "Aguardando",
        "in_progress": "Em atendimento",
        "completed": "Concluído",
        "left": "Saiu da fila",
    }.get(value, value)


def _source_label(value: str) -> str:
    return {"manual": "Manual", "authorized_feed": "Feed autorizado", "demo": "Demonstração"}.get(value, value)
