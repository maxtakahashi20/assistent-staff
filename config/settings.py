"""Persistent application settings backed by SQLite."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from database.connection import Database


DEFAULT_WORK_CHANNELS: dict[str, str] = {
    f"Atendimento {number:02d}": "" for number in range(1, 9)
}


@dataclass(slots=True)
class Settings:
    source_mode: str = "manual"  # manual | json_file
    queue_channel_id: str = ""
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
            value = parsed_channels.get(key, "")
            merged_channels[key] = str(value) if value is not None else ""

        return cls(
            source_mode=str(raw.get("source_mode", defaults.source_mode)),
            queue_channel_id=str(raw.get("queue_channel_id", "")),
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
