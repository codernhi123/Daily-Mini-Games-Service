"""add id, email, and password

Revision ID: 49eefd26e2b9
Revises: 3e588a47adb0
Create Date: 2025-10-08 18:41:57.721707

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49eefd26e2b9'
down_revision: Union[str, Sequence[str], None] = '3e588a47adb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("CREATE SEQUENCE users_id_seq START 1"))
    op.add_column('users', sa.Column('id', sa.Integer, nullable=False, server_default=sa.text("nextval('users_id_seq')")))
    op.add_column('users', sa.Column('email', sa.String(), unique=True, nullable=False))
    op.add_column('users', sa.Column('password', sa.String(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'id')
    op.drop_column('users', 'email')
    op.drop_column('users', 'password')
    op.execute(sa.text("DROP SEQUENCE users_id_seq"))