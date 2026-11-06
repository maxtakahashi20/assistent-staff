"""Typed data structures used by persistence and integrations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True, frozen=True)
class QueuePerson:
    display_name: str
    discord_user_id: str | None = None
    joined_at: str | None = None


@dataclass(slots=True, frozen=True)
class QueueSnapshot:
    people: tuple[QueuePerson, ...]
    helper_voice_channel_id: str | None = None
    generated_at: str | None = None


@dataclass(slots=True, frozen=True)
class QueueEntry:
    id: int
    discord_user_id: str | None
    display_name: str
    joined_at: str
    left_at: str | None
    status: str
    source: str
    notes: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: object) -> "QueueEntry":
        return cls(
            id=int(row["id"]),  # type: ignore[index]
            discord_user_id=row["discord_user_id"],  # type: ignore[index]
            display_name=str(row["display_name"]),  # type: ignore[index]
            joined_at=str(row["joined_at"]),  # type: ignore[index]
            left_at=row["left_at"],  # type: ignore[index]
            status=str(row["status"]),  # type: ignore[index]
            source=str(row["source"]),  # type: ignore[index]
            notes=str(row["notes"]),  # type: ignore[index]
            created_at=str(row["created_at"]),  # type: ignore[index]
            updated_at=str(row["updated_at"]),  # type: ignore[index]
        )
