from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
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


class PropositionModel(Base):
    __tablename__ = "propositions"
    __table_args__ = (
        UniqueConstraint(
            "game_run_id",
            "proposition_key",
            name="propositions_run_key",
        ),
        Index("propositions_run_subject_idx", "game_run_id", "subject_kind", "subject_id"),
    )

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposition_key: Mapped[str] = mapped_column(String(96), nullable=False)
    subject_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[str | None] = mapped_column(String(64))
    predicate: Mapped[str] = mapped_column(String(96), nullable=False)
    canonical_ground_truth: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BeliefModel(Base):
    __tablename__ = "beliefs"
    __table_args__ = (
        UniqueConstraint(
            "game_run_id",
            "proposition_id",
            "holder_kind",
            "holder_id",
            name="beliefs_run_proposition_holder",
        ),
        CheckConstraint("current_version >= 1", name="belief_current_version_positive"),
        Index("beliefs_run_holder_status_idx", "game_run_id", "holder_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposition_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("propositions.id", ondelete="CASCADE"),
        nullable=False,
    )
    holder_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    holder_id: Mapped[str] = mapped_column(String(64), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    contested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BeliefVersionModel(Base):
    __tablename__ = "belief_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["belief_id"],
            ["beliefs.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("version >= 1", name="belief_version_positive"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="belief_version_confidence_range",
        ),
        CheckConstraint("salience >= 0", name="belief_version_salience_nonnegative"),
        Index(
            "belief_versions_run_holder_status_idx",
            "game_run_id",
            "holder_id",
            "status",
        ),
    )

    belief_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_run_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    holder_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_position: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    salience: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embedding_model_id: Mapped[str] = mapped_column(String(96), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ActiveMemoryModel(Base):
    __tablename__ = "active_memories"
    __table_args__ = (
        ForeignKeyConstraint(
            ["belief_id", "belief_version"],
            ["belief_versions.belief_id", "belief_versions.version"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="active_memory_confidence_range",
        ),
        CheckConstraint("salience >= 0", name="active_memory_salience_nonnegative"),
        UniqueConstraint("belief_id", name="active_memories_belief_unique"),
        Index(
            "active_memories_run_holder_status_idx",
            "game_run_id",
            "holder_id",
            "status",
        ),
    )

    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    holder_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    belief_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    belief_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model_id: Mapped[str] = mapped_column(String(96), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    salience: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class GossipTickModel(Base):
    __tablename__ = "gossip_ticks"
    __table_args__ = (
        UniqueConstraint("game_run_id", "tick_number", name="gossip_ticks_run_number"),
    )

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    tick_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hops_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hops_committed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    serialization_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class TransmissionModel(Base):
    __tablename__ = "transmissions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["from_belief_id", "from_version"],
            ["belief_versions.belief_id", "belief_versions.version"],
        ),
        ForeignKeyConstraint(
            ["to_belief_id", "to_version"],
            ["belief_versions.belief_id", "belief_versions.version"],
        ),
        Index("transmissions_run_proposition_idx", "game_run_id", "proposition_id"),
        Index("transmissions_result_idx", "to_belief_id", "to_version"),
    )

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposition_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("propositions.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_belief_id: Mapped[UUID | None] = mapped_column(SQLUUID(as_uuid=True))
    from_version: Mapped[int | None] = mapped_column(Integer)
    to_belief_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    to_version: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_id: Mapped[str | None] = mapped_column(String(64))
    listener_id: Mapped[str] = mapped_column(String(64), nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text)
    retold_text: Mapped[str] = mapped_column(Text, nullable=False)
    mutation_note: Mapped[str | None] = mapped_column(Text)
    trust_at_time: Mapped[float | None] = mapped_column(Float)
    provider_id: Mapped[str] = mapped_column(String(32), nullable=False)
    model_id: Mapped[str] = mapped_column(String(96), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fallback_reason: Mapped[str | None] = mapped_column(String(96))
    inference_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inference_latency_ms: Mapped[float | None] = mapped_column(Float)
    tick_id: Mapped[UUID | None] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("gossip_ticks.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RelationshipModel(Base):
    __tablename__ = "relationships"
    __table_args__ = (
        CheckConstraint("trust >= 0 AND trust <= 1", name="relationship_trust_range"),
        CheckConstraint("affinity >= -1 AND affinity <= 1", name="relationship_affinity_range"),
        CheckConstraint("fear >= 0 AND fear <= 1", name="relationship_fear_range"),
        CheckConstraint("debt >= -1 AND debt <= 1", name="relationship_debt_range"),
    )

    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    a_kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    a_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    b_kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    b_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trust: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    affinity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fear: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    debt: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    faction_alignment: Mapped[str | None] = mapped_column(String(64))
    last_interaction: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalTraceModel(Base):
    __tablename__ = "retrieval_traces"
    __table_args__ = (
        Index("retrieval_traces_run_holder_created_idx", "game_run_id", "holder_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    game_run_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("game_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    holder_id: Mapped[str] = mapped_column(String(64), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    candidate_versions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    selected_versions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    query_plan: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
