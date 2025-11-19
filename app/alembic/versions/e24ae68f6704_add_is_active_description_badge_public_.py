"""add_is_active_description_and_badges_table

Revision ID: e24ae68f6704
Revises: a23e245e430c
Create Date: 2025-11-19 20:06:30.508567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e24ae68f6704'
down_revision: Union[str, Sequence[str], None] = 'a23e245e430c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active and description to api_keys, create badges table."""
    # Add is_active column (default True)
    op.add_column('api_keys', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Add description column (optional)
    op.add_column('api_keys', sa.Column('description', sa.Text(), nullable=True))

    # Create badges table
    op.create_table(
        'badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('badge_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_badges_id'), 'badges', ['id'], unique=False)
    op.create_index(op.f('ix_badges_badge_uuid'), 'badges', ['badge_uuid'], unique=True)
    op.create_index(op.f('ix_badges_api_key_id'), 'badges', ['api_key_id'], unique=True)


def downgrade() -> None:
    """Remove badges table and api_keys columns."""
    # Drop badges table
    op.drop_index(op.f('ix_badges_api_key_id'), table_name='badges')
    op.drop_index(op.f('ix_badges_badge_uuid'), table_name='badges')
    op.drop_index(op.f('ix_badges_id'), table_name='badges')
    op.drop_table('badges')

    # Drop api_keys columns
    op.drop_column('api_keys', 'description')
    op.drop_column('api_keys', 'is_active')
