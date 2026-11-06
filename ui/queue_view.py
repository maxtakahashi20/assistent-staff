from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog,
    QLineEdit, QFormLayout, QMessageBox, QDialogButtonBox,
)

from core.queue_manager import QueueManager
from ui.components.queue_table import QueueTable


class AddPlayerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Adicionar jogador à fila")
        self.setMinimumWidth(390)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: Jogador_123")
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Opcional")
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Opcional")
        form.addRow("Nome do jogador *", self.name_input)
        form.addRow("ID Discord", self.id_input)
        form.addRow("Observação", self.notes_input)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class QueuePage(QWidget):
    def __init__(self, manager: QueueManager) -> None:
        super().__init__()
        self.manager = manager
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(16)
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Gerenciamento da fila")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Registre entradas, inicie e conclua atendimentos.")
        subtitle.setObjectName("Muted")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()
        self.add_button = QPushButton("＋  Adicionar manualmente")
        self.add_button.setObjectName("Primary")
        self.add_button.clicked.connect(self._add_player)
        header.addWidget(self.add_button)
        root.addLayout(header)

        self.table = QueueTable()
        root.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.start_button = QPushButton("▶  Iniciar atendimento")
        self.complete_button = QPushButton("✓  Concluir atendimento")
        self.left_button = QPushButton("Remover da fila")
        self.refresh_button = QPushButton("↻  Atualizar")
        self.start_button.clicked.connect(self._start)
        self.complete_button.clicked.connect(self._complete)
        self.left_button.clicked.connect(self._mark_left)
        self.refresh_button.clicked.connect(self.refresh)
        actions.addWidget(self.start_button)
        actions.addWidget(self.complete_button)
        actions.addWidget(self.left_button)
        actions.addStretch()
        actions.addWidget(self.refresh_button)
        root.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        self.table.populate(self.manager.list_active())

    def _selected(self) -> int | None:
        entry_id = self.table.selected_entry_id()
        if entry_id is None:
            QMessageBox.information(self, "Selecione um jogador", "Selecione um registro na tabela primeiro.")
        return entry_id

    def _add_player(self) -> None:
        dialog = AddPlayerDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.manager.add_manual(
                dialog.name_input.text(),
                dialog.id_input.text(),
                dialog.notes_input.text(),
            )
            self.refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Não foi possível adicionar", str(exc))

    def _start(self) -> None:
        entry_id = self._selected()
        if entry_id is None:
            return
        try:
            self.manager.mark_started(entry_id)
            self.refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Ação não concluída", str(exc))

    def _complete(self) -> None:
        entry_id = self._selected()
        if entry_id is None:
            return
        try:
            self.manager.mark_completed(entry_id)
            self.refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Ação não concluída", str(exc))

    def _mark_left(self) -> None:
        entry_id = self._selected()
        if entry_id is None:
            return
        answer = QMessageBox.question(self, "Remover jogador", "Marcar este jogador como alguém que saiu da fila?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.manager.mark_left(entry_id)
            self.refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Ação não concluída", str(exc))
