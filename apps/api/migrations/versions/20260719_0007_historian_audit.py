"""Add immutable audit records for Town Historian operations.

Revision ID: 20260719_0007
Revises: 20260719_0006
Create Date: 2026-07-19 05:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0007"
down_revision: str | None = "20260719_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historian_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("proposition_key", sa.String(length=96), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("attempted_provider_id", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=True),
        sa.Column("auth_mode", sa.String(length=32), nullable=False),
        sa.Column("cluster_fingerprint", sa.String(length=16), nullable=True),
        sa.Column("managed_mcp", sa.Boolean(), nullable=False),
        sa.Column("sponsor_proof", sa.Boolean(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("fallback_reason", sa.String(length=96), nullable=True),
        sa.Column("query_id", sa.String(length=64), nullable=False),
        sa.Column("result_counts", postgresql.JSONB(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["game_run_id"],
            ["game_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "historian_audits_run_created_idx",
        "historian_audits",
        ["game_run_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "historian_audits_run_created_idx",
        table_name="historian_audits",
    )
    op.drop_table("historian_audits")
