"""Add evidence and provenance-preserving contested belief inputs.

Revision ID: 20260719_0006
Revises: 20260719_0005
Create Date: 2026-07-19 04:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0006"
down_revision: str | None = "20260719_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_key", sa.String(length=96), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::JSONB"),
            nullable=False,
        ),
        sa.Column(
            "discovered_by_player",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
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
        sa.UniqueConstraint(
            "game_run_id",
            "evidence_key",
            name="evidence_run_key",
        ),
    )

    op.create_table(
        "evidence_links",
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "effect IN ('supports', 'contradicts')",
            name="evidence_link_effect",
        ),
        sa.CheckConstraint(
            "weight >= 0 AND weight <= 1",
            name="evidence_link_weight_range",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposition_id"],
            ["propositions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("evidence_id", "proposition_id"),
    )

    op.create_table(
        "belief_inputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("holder_kind", sa.String(length=32), nullable=False),
        sa.Column("holder_id", sa.String(length=64), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.Column("normalized_position", postgresql.JSONB(), nullable=False),
        sa.Column("source_trust", sa.Float(), nullable=False),
        sa.Column("evidence_weight", sa.Float(), nullable=False),
        sa.Column("corroboration", sa.Float(), nullable=False),
        sa.Column("recency", sa.Float(), nullable=False),
        sa.Column("bias_alignment", sa.Float(), nullable=False),
        sa.Column("incoming_strength", sa.Float(), nullable=False),
        sa.Column("classification", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("observed_version", sa.Integer(), nullable=True),
        sa.Column("evaluated_against_version", sa.Integer(), nullable=True),
        sa.Column("resulting_belief_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resulting_version", sa.Integer(), nullable=True),
        sa.Column("transaction_attempts", sa.Integer(), nullable=False),
        sa.Column(
            "recalculated_after_conflict",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_trust >= 0 AND source_trust <= 1",
            name="belief_input_source_trust_range",
        ),
        sa.CheckConstraint(
            "evidence_weight >= -1 AND evidence_weight <= 1",
            name="belief_input_evidence_weight_range",
        ),
        sa.CheckConstraint(
            "corroboration >= 0 AND corroboration <= 1",
            name="belief_input_corroboration_range",
        ),
        sa.CheckConstraint(
            "recency >= 0 AND recency <= 1",
            name="belief_input_recency_range",
        ),
        sa.CheckConstraint(
            "bias_alignment >= -1 AND bias_alignment <= 1",
            name="belief_input_bias_alignment_range",
        ),
        sa.CheckConstraint(
            "incoming_strength >= 0 AND incoming_strength <= 1",
            name="belief_input_strength_range",
        ),
        sa.CheckConstraint(
            "transaction_attempts >= 1",
            name="belief_input_transaction_attempts_positive",
        ),
        sa.ForeignKeyConstraint(
            ["game_run_id"],
            ["game_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposition_id"],
            ["propositions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_belief_id", "resulting_version"],
            ["belief_versions.belief_id", "belief_versions.version"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "belief_inputs_run_proposition_holder_created_idx",
        "belief_inputs",
        ["game_run_id", "proposition_id", "holder_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "belief_inputs_run_proposition_holder_created_idx",
        table_name="belief_inputs",
    )
    op.drop_table("belief_inputs")
    op.drop_table("evidence_links")
    op.drop_table("evidence")
