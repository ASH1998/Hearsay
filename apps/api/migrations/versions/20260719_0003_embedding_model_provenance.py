"""Record the embedding model used for each belief version.

Revision ID: 20260719_0003
Revises: 20260719_0002
Create Date: 2026-07-19 02:18:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0003"
down_revision: str | None = "20260719_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "belief_versions",
        sa.Column(
            "embedding_model_id",
            sa.String(length=96),
            server_default="unknown",
            nullable=False,
        ),
    )
    op.alter_column(
        "belief_versions",
        "embedding_model_id",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("belief_versions", "embedding_model_id")
