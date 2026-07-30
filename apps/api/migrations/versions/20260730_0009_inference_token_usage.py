"""Add Bedrock-compatible inference token usage provenance.

Revision ID: 20260730_0009
Revises: 20260719_0008
Create Date: 2026-07-30 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0009"
down_revision: str | None = "20260719_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transmissions",
        sa.Column("inference_input_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "transmissions",
        sa.Column("inference_output_tokens", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "transmissions_input_tokens_nonnegative",
        "transmissions",
        "inference_input_tokens IS NULL OR inference_input_tokens >= 0",
    )
    op.create_check_constraint(
        "transmissions_output_tokens_nonnegative",
        "transmissions",
        "inference_output_tokens IS NULL OR inference_output_tokens >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "transmissions_output_tokens_nonnegative",
        "transmissions",
        type_="check",
    )
    op.drop_constraint(
        "transmissions_input_tokens_nonnegative",
        "transmissions",
        type_="check",
    )
    op.drop_column("transmissions", "inference_output_tokens")
    op.drop_column("transmissions", "inference_input_tokens")
