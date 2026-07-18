"""Add explainable elections, votes, and exact decision inputs.

Revision ID: 20260719_0008
Revises: 20260719_0007
Create Date: 2026-07-19 06:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0008"
down_revision: str | None = "20260719_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "elections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_votes", sa.Integer(), nullable=False),
        sa.Column("rhea_votes", sa.Integer(), nullable=False),
        sa.Column("winner", sa.String(length=16), nullable=False),
        sa.Column("tie_favors_rhea", sa.Boolean(), nullable=False),
        sa.Column("ending_key", sa.String(length=32), nullable=False),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "player_votes >= 0 AND player_votes <= 20",
            name="elections_player_votes_range",
        ),
        sa.CheckConstraint(
            "rhea_votes >= 0 AND rhea_votes <= 20",
            name="elections_rhea_votes_range",
        ),
        sa.ForeignKeyConstraint(
            ["game_run_id"],
            ["game_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_run_id", name="elections_run_unique"),
    )
    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("election_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voter_id", sa.String(length=64), nullable=False),
        sa.Column("choice", sa.String(length=16), nullable=False),
        sa.Column("player_score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["election_id"],
            ["elections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["game_run_id"],
            ["game_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "election_id",
            "voter_id",
            name="votes_election_voter",
        ),
    )
    op.create_index(
        "votes_run_choice_idx",
        "votes",
        ["game_run_id", "choice"],
    )
    op.create_table(
        "vote_inputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_kind", sa.String(length=24), nullable=False),
        sa.Column("input_key", sa.String(length=96), nullable=False),
        sa.Column("input_value", postgresql.JSONB(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("contribution", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("belief_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("belief_version", sa.Integer(), nullable=True),
        sa.Column("decisive_rank", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "decisive_rank IS NULL OR (decisive_rank >= 1 AND decisive_rank <= 3)",
            name="vote_inputs_decisive_rank_range",
        ),
        sa.ForeignKeyConstraint(
            ["belief_id", "belief_version"],
            ["belief_versions.belief_id", "belief_versions.version"],
        ),
        sa.ForeignKeyConstraint(
            ["game_run_id"],
            ["game_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vote_id"],
            ["votes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "vote_inputs_vote_rank_idx",
        "vote_inputs",
        ["vote_id", "decisive_rank"],
    )


def downgrade() -> None:
    op.drop_index("vote_inputs_vote_rank_idx", table_name="vote_inputs")
    op.drop_table("vote_inputs")
    op.drop_index("votes_run_choice_idx", table_name="votes")
    op.drop_table("votes")
    op.drop_table("elections")
