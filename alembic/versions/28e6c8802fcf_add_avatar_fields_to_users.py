"""add avatar fields to users

Revision ID: 28e6c8802fcf
Revises: 938f4ce2cc82
Create Date: 2025-10-31 02:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "28e6c8802fcf"
down_revision = "938f4ce2cc82"  # replace this with your last revision’s ID
branch_labels = None
depends_on = None


def upgrade():
    # --- Add new columns ---
    op.add_column(
        "users",
        sa.Column("has_avatar", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.add_column(
        "users",
        sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    # --- Remove columns if rolled back ---
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "has_avatar")

