"""merge conflicting migrations

Revision ID: 469f9dc1be94
Revises: 3a1b2c3d4e5f
Create Date: 2025-11-20 14:18:40.712857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '469f9dc1be94'
down_revision: Union[str, Sequence[str], None] = '3a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
