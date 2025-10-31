"""add users_v1 legacy table

Revision ID: 60508625bbf7
Revises: 938f4ce2cc82
Create Date: 2025-10-31 00:47:35.600571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60508625bbf7'
down_revision: Union[str, Sequence[str], None] = '938f4ce2cc82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users_v1',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('name'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('users_v1')
