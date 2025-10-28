"""create events table

Revision ID: 6b1a0e7c2e88
Revises: c7e4a9f2b18d
Create Date: 2025-10-26 23:59:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '81f34854c5bf'
down_revision: Union[str, Sequence[str], None] = 'c7e4a9f2b18d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('when', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('user', sa.String(), nullable=True),
    )
    op.create_index('ix_events_when', 'events', ['when'])
    op.create_index('ix_events_type', 'events', ['type'])
    op.create_index('ix_events_source', 'events', ['source'])
    op.create_index('ix_events_user', 'events', ['user'])
    op.create_index('ix_events_when_user', 'events', ['when', 'user'])
    op.create_index('ix_events_type_source_when', 'events', ['type', 'source', 'when'])


def downgrade() -> None:
    op.drop_index('ix_events_type_source_when', table_name='events')
    op.drop_index('ix_events_when_user', table_name='events')
    op.drop_index('ix_events_user', table_name='events')
    op.drop_index('ix_events_source', table_name='events')
    op.drop_index('ix_events_type', table_name='events')
    op.drop_index('ix_events_when', table_name='events')
    op.drop_table('events')

