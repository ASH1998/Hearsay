"""Create the active-memory vector-search projection.

Revision ID: 20260719_0004
Revises: 20260719_0003
Create Date: 2026-07-19 02:42:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0004"
down_revision: str | None = "20260719_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "active_memories",
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("holder_id", sa.String(length=64), nullable=False),
        sa.Column("belief_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("belief_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("embedding_model_id", sa.String(length=96), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("salience", sa.Float(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="active_memory_confidence_range",
        ),
        sa.CheckConstraint(
            "salience >= 0",
            name="active_memory_salience_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["belief_id", "belief_version"],
            ["belief_versions.belief_id", "belief_versions.version"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["game_run_id"],
            ["game_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("game_run_id", "holder_id", "belief_id"),
        sa.UniqueConstraint("belief_id", name="active_memories_belief_unique"),
    )
    op.create_index(
        "active_memories_run_holder_status_idx",
        "active_memories",
        ["game_run_id", "holder_id", "status"],
    )
    op.execute(
        "CREATE VECTOR INDEX active_memories_retrieval_vector_idx "
        "ON active_memories "
        "(game_run_id, holder_id, status, embedding vector_cosine_ops)"
    )
    op.execute("DROP INDEX belief_versions@belief_versions_retrieval_vector_idx")


def downgrade() -> None:
    op.execute("SET sql_safe_updates = false")
    op.execute(
        "CREATE VECTOR INDEX belief_versions_retrieval_vector_idx "
        "ON belief_versions "
        "(game_run_id, holder_id, status, embedding vector_cosine_ops)"
    )
    op.execute("DROP INDEX active_memories@active_memories_retrieval_vector_idx")
    op.drop_index(
        "active_memories_run_holder_status_idx",
        table_name="active_memories",
    )
    op.drop_table("active_memories")
