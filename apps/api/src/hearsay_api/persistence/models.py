from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PlayerModel(Base):
    __tablename__ = "players"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(40), nullable=False)
    credibility: Mapped[float] = mapped_column(default=0.5, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class GameRunModel(Base):
    __tablename__ = "game_runs"
    __table_args__ = (
        CheckConstraint("action_count >= 0 AND action_count <= 18", name="action_count_range"),
        CheckConstraint("day >= 1 AND day <= 3", name="day_range"),
        CheckConstraint("revision >= 0", name="revision_nonnegative"),
        Index("game_runs_player_status_idx", "player_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    player_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_key: Mapped[str] = mapped_column(
        String(64), default="greyhaven-election", nullable=False
    )
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    phase: Mapped[str] = mapped_column(String(16), default="morning", nullable=False)
    action_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    world_tick: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_location_id: Mapped[str] = mapped_column(String(64), nullable=False)
    weather: Mapped[str] = mapped_column(String(16), default="clear", nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActionModel(Base):
    __tablename__ = "actions"
    __table_args__ = (
        UniqueConstraint(
            "game_run_id",
            "idempotency_key",
            name="actions_run_idempotency_key",
        ),
        Index("actions_run_created_idx", "game_run_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    verb: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64))
    content: Mapped[str | None] = mapped_column(Text)
    consumed_time: Mapped[bool] = mapped_column(Boolean, nullable=False)
    before_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    after_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    before_action_count: Mapped[int] = mapped_column(Integer, nullable=False)
    after_action_count: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EventModel(Base):
    __tablename__ = "events"
    __table_args__ = (Index("events_run_tick_idx", "game_run_id", "world_tick"),)

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), default="public", nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    world_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
