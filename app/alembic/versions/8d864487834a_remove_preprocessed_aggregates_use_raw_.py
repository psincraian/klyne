"""remove_preprocessed_aggregates_use_raw_data_only

Revision ID: 8d864487834a
Revises: e2420669e7ad
Create Date: 2025-08-02 20:57:00.606733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d864487834a'
down_revision: Union[str, Sequence[str], None] = 'e2420669e7ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove aggregate tables and preprocessing columns."""
    # Drop aggregate tables that are no longer needed
    op.drop_table('package_version_stats')
    op.drop_table('operating_system_stats')
    op.drop_table('python_version_stats')
    op.drop_table('daily_package_stats')
    
    # Remove preprocessing columns from analytics_events
    op.drop_index('idx_analytics_processing', table_name='analytics_events')
    op.drop_column('analytics_events', 'processed')
    op.drop_column('analytics_events', 'processed_at')


def downgrade() -> None:
    """Restore aggregate tables and preprocessing columns."""
    # Add back preprocessing columns to analytics_events
    op.add_column('analytics_events', sa.Column('processed', sa.Boolean(), nullable=True, default=False))
    op.add_column('analytics_events', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_analytics_processing', 'analytics_events', ['processed', 'received_at'], unique=False)
    
    # Recreate aggregate tables (simplified versions)
    op.create_table('daily_package_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('package_name', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_events', sa.BigInteger(), nullable=False),
        sa.Column('unique_sessions', sa.BigInteger(), nullable=False),
        sa.Column('unique_users_estimate', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('package_name', 'api_key', 'date', name='uq_daily_package_stats')
    )
