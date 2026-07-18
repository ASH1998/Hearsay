"""Add structured-inference provenance to rumor transmissions.

Revision ID: 20260719_0005
Revises: 20260719_0004
Create Date: 2026-07-19 03:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0005"
down_revision: str | None = "20260719_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transmissions",
        sa.Column(
            "provider_id",
            sa.String(length=32),
            server_default="deterministic",
            nullable=False,
        ),
    )
    op.add_column(
        "transmissions",
        sa.Column(
            "fallback_used",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "transmissions",
        sa.Column("fallback_reason", sa.String(length=96), nullable=True),
    )
    op.add_column(
        "transmissions",
        sa.Column(
            "inference_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "transmissions",
        sa.Column("inference_latency_ms", sa.Float(), nullable=True),
    )
    op.alter_column("transmissions", "provider_id", server_default=None)
    op.alter_column("transmissions", "fallback_used", server_default=None)
    op.alter_column("transmissions", "inference_attempts", server_default=None)


def downgrade() -> None:
    op.drop_column("transmissions", "inference_latency_ms")
    op.drop_column("transmissions", "inference_attempts")
    op.drop_column("transmissions", "fallback_reason")
    op.drop_column("transmissions", "fallback_used")
    op.drop_column("transmissions", "provider_id")
