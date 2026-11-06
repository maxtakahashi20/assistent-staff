from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from core.queue_manager import QueueManager
from ui.components.queue_table import QueueTable


class HistoryPage(QWidget):
    def __init__(self, manager: QueueManager) -> None:
        super().__init__()
        self.manager = manager
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(16)
        header = QHBoxLayout()
        col = QVBoxLayout()
        title = QLabel("Histórico de atendimentos")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Registros locais mantidos neste computador.")
        subtitle.setObjectName("Muted")
        col.addWidget(title)
        col.addWidget(subtitle)
        header.addLayout(col)
        header.addStretch()
        refresh = QPushButton("↻  Atualizar")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        root.addLayout(header)
        self.table = QueueTable(selectable=False)
        root.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        self.table.populate(self.manager.list_history(300))
