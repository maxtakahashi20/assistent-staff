"""Persistent application settings backed by SQLite."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from database.connection import Database


DEFAULT_QUEUE_CHANNEL_ID = "1305663080826535937"  # Aguardando Suporte

DEFAULT_WORK_CHANNELS: dict[str, str] = {
    "Atendimento 01": "1305663051990827039",
    "Atendimento 02": "1305663051990827039",
    "Atendimento 03": "1305663056868544593",
    "Atendimento 04": "1305663065647349811",
    "Atendimento 05": "1305663061721616425",
    "Atendimento 06": "1305663067811745943",
    "Atendimento 07": "1305663070063824927",
    "Atendimento 08": "1305663071422775339",
}


@dataclass(slots=True)
class Settings:
    source_mode: str = "manual"  # manual | json_file
    queue_channel_id: str = DEFAULT_QUEUE_CHANNEL_ID
    work_channels: dict[str, str] = field(
        default_factory=lambda: DEFAULT_WORK_CHANNELS.copy()
    )
    feed_path: str = ""
    sound_enabled: bool = True
    desktop_notifications: bool = True
    sound_path: str = ""
    start_with_windows: bool = False
    refresh_interval_seconds: int = 3
    theme: str = "dark"

    @classmethod
    def load(cls, db: Database) -> "Settings":
        raw = db.get_all_settings()
        defaults = cls()
        channels = raw.get("work_channels")
        try:
            parsed_channels = dict(channels) if isinstance(channels, dict) else {}
        except (TypeError, ValueError):
            parsed_channels = {}

        merged_channels = DEFAULT_WORK_CHANNELS.copy()
        for key in merged_channels:
            value = parsed_channels.get(key)
            if value:  # campo vazio salvo volta ao ID padrão
                merged_channels[key] = str(value)

        return cls(
            source_mode=str(raw.get("source_mode", defaults.source_mode)),
            queue_channel_id=str(raw.get("queue_channel_id") or DEFAULT_QUEUE_CHANNEL_ID),
            work_channels=merged_channels,
            feed_path=str(raw.get("feed_path", "")),
            sound_enabled=bool(raw.get("sound_enabled", defaults.sound_enabled)),
            desktop_notifications=bool(
                raw.get("desktop_notifications", defaults.desktop_notifications)
            ),
            sound_path=str(raw.get("sound_path", "")),
            start_with_windows=bool(
                raw.get("start_with_windows", defaults.start_with_windows)
            ),
            refresh_interval_seconds=_clamp_interval(
                raw.get("refresh_interval_seconds", defaults.refresh_interval_seconds)
            ),
            theme=str(raw.get("theme", defaults.theme)),
        )

    def save(self, db: Database) -> None:
        payload: dict[str, Any] = asdict(self)
        db.save_settings(payload)


def _clamp_interval(value: Any) -> int:
    try:
        return max(1, min(60, int(value)))
    except (TypeError, ValueError):
        return 3
