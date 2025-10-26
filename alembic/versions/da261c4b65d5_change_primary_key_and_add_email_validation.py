"""change primary key and add email validation

Revision ID: da261c4b65d5
Revises: 49eefd26e2b9
Create Date: 2025-10-23 10:37:57.721707

"""
from typing import Sequence, Union

from alembic import op
# import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da261c4b65d5'
down_revision: Union[str, Sequence[str], None] = '49eefd26e2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('users_pkey', 'users', type_='primary')
    op.create_primary_key('users_pkey', 'users', ['id'])
    op.create_check_constraint('valid_email_check', 'users', "email ~ '^[^@]+@[^@]+\\.[^@]+$'")
    op.create_unique_constraint('users_name_key', 'users', ['name'])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('users_name_key', 'users', type_='unique')
    op.drop_constraint('valid_email_check', 'users', type_='check')    
    op.drop_constraint('users_pkey', 'users', type_='primary')
    op.create_primary_key('users_pkey', 'users', ['name'])