from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFormLayout, QLineEdit, QComboBox, QCheckBox, QSpinBox, QFileDialog,
    QMessageBox, QGridLayout,
)

from config.settings import Settings
from core.notifications import NotificationService
from database.connection import Database


class SettingsPage(QWidget):
    def __init__(self, db: Database, settings: Settings, on_saved) -> None:
        super().__init__()
        self.db = db
        self.settings = settings
        self.on_saved = on_saved
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(16)

        title = QLabel("Configurações")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Configure a fonte de dados, as canaletas e os alertas locais.")
        subtitle.setObjectName("Muted")
        root.addWidget(title)
        root.addWidget(subtitle)

        source_card = QFrame()
        source_card.setObjectName("Panel")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(18, 16, 18, 16)
        source_title = QLabel("Fonte de dados")
        source_title.setObjectName("SectionTitle")
        source_layout.addWidget(source_title)
        source_form = QFormLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItem("Acompanhamento manual", "manual")
        self.source_combo.addItem("Feed JSON autorizado", "json_file")
        self.feed_path = QLineEdit(settings.feed_path)
        self.feed_path.setPlaceholderText("Caminho do arquivo queue-feed.json")
        browse = QPushButton("Selecionar arquivo")
        browse.clicked.connect(self._browse_feed)
        feed_row = QHBoxLayout()
        feed_row.addWidget(self.feed_path, 1)
        feed_row.addWidget(browse)
        feed_wrapper = QWidget()
        feed_wrapper.setLayout(feed_row)
        source_form.addRow("Modo de operação", self.source_combo)
        source_form.addRow("Arquivo do feed", feed_wrapper)
        source_layout.addLayout(source_form)
        self.feed_hint = QLabel(
            "O arquivo deve ser produzido por uma integração oficial autorizada pelo servidor. "
            "Não informe token de usuário nem credenciais do Discord aqui."
        )
        self.feed_hint.setWordWrap(True)
        self.feed_hint.setObjectName("Muted")
        source_layout.addWidget(self.feed_hint)
        root.addWidget(source_card)

        channels_card = QFrame()
        channels_card.setObjectName("Panel")
        channels_layout = QVBoxLayout(channels_card)
        channels_layout.setContentsMargins(18, 16, 18, 16)
        channels_title = QLabel("IDs das salas")
        channels_title.setObjectName("SectionTitle")
        channels_layout.addWidget(channels_title)
        self.queue_id_input = QLineEdit(settings.queue_channel_id)
        self.queue_id_input.setPlaceholderText("ID da sala Aguardando Suporte")
        channels_layout.addWidget(QLabel("Aguardando Suporte"))
        channels_layout.addWidget(self.queue_id_input)
        channels_layout.addWidget(QLabel("Canaletas de atendimento"))
        self.channel_inputs: dict[str, QLineEdit] = {}
        grid = QGridLayout()
        for index in range(1, 9):
            channel_name = f"Atendimento {index:02d}"
            label = QLabel(channel_name)
            field = QLineEdit(settings.work_channels.get(channel_name, ""))
            field.setPlaceholderText("ID da sala")
            self.channel_inputs[channel_name] = field
            grid.addWidget(label, (index - 1) // 2, ((index - 1) % 2) * 2)
            grid.addWidget(field, (index - 1) // 2, ((index - 1) % 2) * 2 + 1)
        channels_layout.addLayout(grid)
        root.addWidget(channels_card)

        alerts_card = QFrame()
        alerts_card.setObjectName("Panel")
        alerts_layout = QVBoxLayout(alerts_card)
        alerts_layout.setContentsMargins(18, 16, 18, 16)
        alerts_title = QLabel("Alertas e aparência")
        alerts_title.setObjectName("SectionTitle")
        alerts_layout.addWidget(alerts_title)
        alerts_form = QFormLayout()
        self.sound_check = QCheckBox("Emitir alerta sonoro")
        self.sound_check.setChecked(settings.sound_enabled)
        self.desktop_check = QCheckBox("Exibir notificação na área de trabalho")
        self.desktop_check.setChecked(settings.desktop_notifications)
        self.startup_check = QCheckBox("Iniciar com o Windows")
        self.startup_check.setChecked(settings.start_with_windows)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setSuffix(" segundos")
        self.interval_spin.setValue(settings.refresh_interval_seconds)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Escuro", "dark")
        self.theme_combo.addItem("Claro", "light")
        self._set_combo_data(self.theme_combo, settings.theme)
        self.sound_path_input = QLineEdit(settings.sound_path)
        self.sound_path_input.setPlaceholderText("Opcional: arquivo .wav")
        sound_browse = QPushButton("Procurar")
        sound_browse.clicked.connect(self._browse_sound)
        sound_test = QPushButton("Testar som")
        sound_test.clicked.connect(self._test_sound)
        sound_row_layout = QHBoxLayout()
        sound_row_layout.addWidget(self.sound_path_input, 1)
        sound_row_layout.addWidget(sound_browse)
        sound_row_layout.addWidget(sound_test)
        sound_wrapper = QWidget()
        sound_wrapper.setLayout(sound_row_layout)
        alerts_form.addRow("Notificação", self.desktop_check)
        alerts_form.addRow("Som", self.sound_check)
        alerts_form.addRow("Arquivo de som", sound_wrapper)
        alerts_form.addRow("Atualização", self.interval_spin)
        alerts_form.addRow("Inicialização", self.startup_check)
        alerts_form.addRow("Tema", self.theme_combo)
        alerts_layout.addLayout(alerts_form)
        root.addWidget(alerts_card)

        footer = QHBoxLayout()
        footer.addStretch()
        save = QPushButton("Salvar configurações")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        footer.addWidget(save)
        root.addLayout(footer)
        root.addStretch(1)
        self._set_combo_data(self.source_combo, settings.source_mode)

    @staticmethod
    def _set_combo_data(combo: QComboBox, data: str) -> None:
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _browse_feed(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar feed autorizado", "", "Arquivo JSON (*.json)")
        if path:
            self.feed_path.setText(path)
            self.source_combo.setCurrentIndex(self.source_combo.findData("json_file"))

    def _browse_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar som", "", "Áudio WAV (*.wav)")
        if path:
            self.sound_path_input.setText(path)

    def _test_sound(self) -> None:
        NotificationService.play_sound(self.sound_path_input.text().strip())

    def _save(self) -> None:
        source_mode = str(self.source_combo.currentData())
        feed_path = self.feed_path.text().strip()
        if source_mode == "json_file" and not feed_path:
            QMessageBox.warning(self, "Feed não configurado", "Informe o caminho do arquivo JSON autorizado.")
            return

        channels = {name: field.text().strip() for name, field in self.channel_inputs.items()}
        self.settings.source_mode = source_mode
        self.settings.feed_path = feed_path
        self.settings.queue_channel_id = self.queue_id_input.text().strip()
        self.settings.work_channels = channels
        self.settings.sound_enabled = self.sound_check.isChecked()
        self.settings.desktop_notifications = self.desktop_check.isChecked()
        self.settings.sound_path = self.sound_path_input.text().strip()
        self.settings.start_with_windows = self.startup_check.isChecked()
        self.settings.refresh_interval_seconds = self.interval_spin.value()
        self.settings.theme = str(self.theme_combo.currentData())
        self.settings.save(self.db)

        try:
            _configure_windows_startup(self.settings.start_with_windows)
        except OSError as exc:
            QMessageBox.warning(
                self, "Inicialização do Windows",
                f"As demais configurações foram salvas, mas não foi possível alterar a inicialização automática: {exc}",
            )
        self.on_saved(self.settings)
        QMessageBox.information(self, "Configurações salvas", "As configurações foram salvas localmente.")


def _configure_windows_startup(enabled: bool) -> None:
    if sys.platform != "win32":
        if enabled:
            raise OSError("A inicialização automática está disponível apenas no Windows.")
        return
    import winreg
    import subprocess

    run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value_name = "CitySupportAssistant"
    if getattr(sys, "frozen", False):
        command = subprocess.list2cmdline([sys.executable])
    else:
        app_file = Path(__file__).resolve().parents[1] / "app.py"
        python_exe = Path(sys.executable)
        pythonw_exe = python_exe.with_name("pythonw.exe")
        launcher = pythonw_exe if pythonw_exe.exists() else python_exe
        command = subprocess.list2cmdline([str(launcher), str(app_file)])
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, value_name)
            except FileNotFoundError:
                pass
