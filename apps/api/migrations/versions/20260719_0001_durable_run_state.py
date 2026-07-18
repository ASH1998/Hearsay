"""Create durable player, run, action, and event state.

Revision ID: 20260719_0001
Revises:
Create Date: 2026-07-19 00:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=40), nullable=False),
        sa.Column("credibility", sa.Float(), nullable=False),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "game_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_key", sa.String(length=64), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("action_count", sa.Integer(), nullable=False),
        sa.Column("world_tick", sa.Integer(), nullable=False),
        sa.Column("current_location_id", sa.String(length=64), nullable=False),
        sa.Column("weather", sa.String(length=16), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "action_count >= 0 AND action_count <= 18",
            name="action_count_range",
        ),
        sa.CheckConstraint("day >= 1 AND day <= 3", name="day_range"),
        sa.CheckConstraint("revision >= 0", name="revision_nonnegative"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "game_runs_player_status_idx",
        "game_runs",
        ["player_id", "status"],
        unique=False,
    )

    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verb", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("consumed_time", sa.Boolean(), nullable=False),
        sa.Column("before_revision", sa.Integer(), nullable=False),
        sa.Column("after_revision", sa.Integer(), nullable=False),
        sa.Column("before_action_count", sa.Integer(), nullable=False),
        sa.Column("after_action_count", sa.Integer(), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_run_id"], ["game_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_run_id",
            "idempotency_key",
            name="actions_run_idempotency_key",
        ),
    )
    op.create_index(
        "actions_run_created_idx",
        "actions",
        ["game_run_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("world_tick", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_run_id"], ["game_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "events_run_tick_idx",
        "events",
        ["game_run_id", "world_tick"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("events_run_tick_idx", table_name="events")
    op.drop_table("events")
    op.drop_index("actions_run_created_idx", table_name="actions")
    op.drop_table("actions")
    op.drop_index("game_runs_player_status_idx", table_name="game_runs")
    op.drop_table("game_runs")
    op.drop_table("players")
