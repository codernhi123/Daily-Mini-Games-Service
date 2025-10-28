"""add jwt column

Revision ID: e9cf9d999836
Revises: 81f34854c5bf
Create Date: 2025-10-27 03:14:27.922233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9cf9d999836'
down_revision: Union[str, Sequence[str], None] = '81f34854c5bf'
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
