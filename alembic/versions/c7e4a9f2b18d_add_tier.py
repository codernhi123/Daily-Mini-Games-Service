"""add tier

Revision ID: c7e4a9f2b18d
Revises: da261c4b65d5
Create Date: 2025-10-26 11:23:57.721707

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e4a9f2b18d'
down_revision: Union[str, Sequence[str], None] = 'da261c4b65d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('tier', sa.Integer, nullable=False, server_default="1"))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'tier')
