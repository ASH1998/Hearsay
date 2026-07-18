"""Create the immutable belief graph and scoped vector-memory spine.

Revision ID: 20260719_0002
Revises: 20260719_0001
Create Date: 2026-07-19 02:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0002"
down_revision: str | None = "20260719_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "propositions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposition_key", sa.String(length=96), nullable=False),
        sa.Column("subject_kind", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=True),
        sa.Column("predicate", sa.String(length=96), nullable=False),
        sa.Column("canonical_ground_truth", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_run_id"], ["game_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_run_id", "proposition_key", name="propositions_run_key"),
    )
    op.create_index(
        "propositions_run_subject_idx",
        "propositions",
        ["game_run_id", "subject_kind", "subject_id"],
    )

    op.create_table(
        "beliefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("holder_kind", sa.String(length=32), nullable=False),
        sa.Column("holder_id", sa.String(length=64), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("contested", sa.Boolean(), nullable=False),
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
        sa.CheckConstraint("current_version >= 1", name="belief_current_version_positive"),
        sa.ForeignKeyConstraint(["game_run_id"], ["game_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposition_id"], ["propositions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_run_id",
            "proposition_id",
            "holder_kind",
            "holder_id",
            name="beliefs_run_proposition_holder",
        ),
    )
    op.create_index(
        "beliefs_run_holder_status_idx",
        "beliefs",
        ["game_run_id", "holder_id", "status"],
    )

    op.create_table(
        "belief_versions",
        sa.Column("belief_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("holder_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.Column("normalized_position", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("salience", sa.Float(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="belief_version_confidence_range",
        ),
        sa.CheckConstraint("salience >= 0", name="belief_version_salience_nonnegative"),
        sa.CheckConstraint("version >= 1", name="belief_version_positive"),
        sa.ForeignKeyConstraint(["belief_id"], ["beliefs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("belief_id", "version"),
    )
    op.create_index(
        "belief_versions_run_holder_status_idx",
        "belief_versions",
        ["game_run_id", "holder_id", "status"],
    )
    op.execute(
        "CREATE VECTOR INDEX belief_versions_retrieval_vector_idx "
        "ON belief_versions "
        "(game_run_id, holder_id, status, embedding vector_cosine_ops)"
    )

    op.create_table(
        "gossip_ticks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tick_number", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hops_attempted", sa.Integer(), nullable=False),
        sa.Column("hops_committed", sa.Integer(), nullable=False),
        sa.Column("serialization_retries", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["game_run_id"], ["game_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_run_id", "tick_number", name="gossip_ticks_run_number"),
    )

    op.create_table(
        "transmissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_belief_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_version", sa.Integer(), nullable=True),
        sa.Column("to_belief_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_version", sa.Integer(), nullable=False),
        sa.Column("speaker_id", sa.String(length=64), nullable=True),
        sa.Column("listener_id", sa.String(length=64), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("retold_text", sa.Text(), nullable=False),
        sa.Column("mutation_note", sa.Text(), nullable=True),
        sa.Column("trust_at_time", sa.Float(), nullable=True),
        sa.Column("model_id", sa.String(length=96), nullable=False),
        sa.Column("tick_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["from_belief_id", "from_version"],
            ["belief_versions.belief_id", "belief_versions.version"],
        ),
        sa.ForeignKeyConstraint(["game_run_id"], ["game_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposition_id"], ["propositions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tick_id"], ["gossip_ticks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["to_belief_id", "to_version"],
            ["belief_versions.belief_id", "belief_versions.version"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "transmissions_run_proposition_idx",
        "transmissions",
        ["game_run_id", "proposition_id"],
    )
    op.create_index(
        "transmissions_result_idx",
        "transmissions",
        ["to_belief_id", "to_version"],
    )

    op.create_table(
        "relationships",
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("a_kind", sa.String(length=32), nullable=False),
        sa.Column("a_id", sa.String(length=64), nullable=False),
        sa.Column("b_kind", sa.String(length=32), nullable=False),
        sa.Column("b_id", sa.String(length=64), nullable=False),
        sa.Column("trust", sa.Float(), nullable=False),
        sa.Column("affinity", sa.Float(), nullable=False),
        sa.Column("fear", sa.Float(), nullable=False),
        sa.Column("debt", sa.Float(), nullable=False),
        sa.Column("faction_alignment", sa.String(length=64), nullable=True),
        sa.Column("last_interaction", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "affinity >= -1 AND affinity <= 1",
            name="relationship_affinity_range",
        ),
        sa.CheckConstraint("debt >= -1 AND debt <= 1", name="relationship_debt_range"),
        sa.CheckConstraint("fear >= 0 AND fear <= 1", name="relationship_fear_range"),
        sa.CheckConstraint("trust >= 0 AND trust <= 1", name="relationship_trust_range"),
        sa.ForeignKeyConstraint(["game_run_id"], ["game_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_run_id", "a_kind", "a_id", "b_kind", "b_id"),
    )

    op.create_table(
        "retrieval_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("holder_id", sa.String(length=64), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("query_embedding", Vector(384), nullable=False),
        sa.Column("candidate_versions", postgresql.JSONB(), nullable=False),
        sa.Column("selected_versions", postgresql.JSONB(), nullable=False),
        sa.Column("query_plan", sa.Text(), nullable=True),
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
        "retrieval_traces_run_holder_created_idx",
        "retrieval_traces",
        ["game_run_id", "holder_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("retrieval_traces_run_holder_created_idx", table_name="retrieval_traces")
    op.drop_table("retrieval_traces")
    op.drop_table("relationships")
    op.drop_index("transmissions_result_idx", table_name="transmissions")
    op.drop_index("transmissions_run_proposition_idx", table_name="transmissions")
    op.drop_table("transmissions")
    op.drop_table("gossip_ticks")
    op.execute("DROP INDEX belief_versions@belief_versions_retrieval_vector_idx")
    op.drop_index("belief_versions_run_holder_status_idx", table_name="belief_versions")
    op.drop_table("belief_versions")
    op.drop_index("beliefs_run_holder_status_idx", table_name="beliefs")
    op.drop_table("beliefs")
    op.drop_index("propositions_run_subject_idx", table_name="propositions")
    op.drop_table("propositions")
