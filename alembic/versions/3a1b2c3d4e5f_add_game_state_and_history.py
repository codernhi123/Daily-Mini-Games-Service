"""add game state and history tables

Revision ID: 3a1b2c3d4e5f
Revises: 28e6c8802fcf
Create Date: 2025-11-14 00:35:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3a1b2c3d4e5f"
down_revision = "1f3996803bd5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_type", sa.String(), nullable=False),
        sa.Column("last_played", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_play_time", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "game_type", name="uq_game_state_user_game"),
    )
    op.create_index("ix_game_state_user_game", "game_state", ["user_id", "game_type"])

    op.create_table(
        "game_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_type", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_game_history_user_game_date",
        "game_history",
        ["user_id", "game_type", "played_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_game_history_user_game_date", table_name="game_history")
    op.drop_table("game_history")

    op.drop_index("ix_game_state_user_game", table_name="game_state")
    op.drop_table("game_state")