"""add jwt column

Revision ID: e9cf9d999836
Revises: c7e4a9f2b18d
Create Date: 2025-10-27 03:14:27.922233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9cf9d999836'
down_revision: Union[str, Sequence[str], None] = 'c7e4a9f2b18d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('active_jwt', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'active_jwt')
    # ### end Alembic commands ###
