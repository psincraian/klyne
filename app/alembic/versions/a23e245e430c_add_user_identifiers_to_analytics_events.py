"""add_user_identifiers_to_analytics_events

Add fields for tracking unique users via installation IDs and fingerprint hashes.
Enables pseudonymous tracking of unique installations for package analytics.

Revision ID: a23e245e430c
Revises: 9bd01edd5933
Create Date: 2025-10-31 22:06:27.212777

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a23e245e430c'
down_revision: Union[str, Sequence[str], None] = '9bd01edd5933'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user identifier fields to analytics_events table."""
    # Add new columns for unique user tracking
    op.add_column(
        'analytics_events',
        sa.Column('installation_id', UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'analytics_events',
        sa.Column('fingerprint_hash', sa.String(length=64), nullable=True)
    )
    op.add_column(
        'analytics_events',
        sa.Column('user_identifier', sa.String(length=100), nullable=True)
    )

    # Create indexes for efficient unique user queries
    op.create_index(
        'idx_analytics_user_identifier',
        'analytics_events',
        ['user_identifier'],
        unique=False
    )
    op.create_index(
        'idx_analytics_user_identifier_date',
        'analytics_events',
        ['api_key', 'user_identifier', 'event_timestamp'],
        unique=False
    )
    op.create_index(
        'idx_analytics_installation_id',
        'analytics_events',
        ['installation_id'],
        unique=False
    )
    op.create_index(
        'idx_analytics_fingerprint',
        'analytics_events',
        ['fingerprint_hash'],
        unique=False
    )


def downgrade() -> None:
    """Remove user identifier fields from analytics_events table."""
    # Drop indexes first
    op.drop_index('idx_analytics_fingerprint', table_name='analytics_events')
    op.drop_index('idx_analytics_installation_id', table_name='analytics_events')
    op.drop_index('idx_analytics_user_identifier_date', table_name='analytics_events')
    op.drop_index('idx_analytics_user_identifier', table_name='analytics_events')

    # Drop columns
    op.drop_column('analytics_events', 'user_identifier')
    op.drop_column('analytics_events', 'fingerprint_hash')
    op.drop_column('analytics_events', 'installation_id')
