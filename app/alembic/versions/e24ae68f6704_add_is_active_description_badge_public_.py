"""add_is_active_description_badge_public_to_api_keys

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
    """Add is_active, description, badge_public, and badge_uuid columns to api_keys table."""
    # Add is_active column (default True)
    op.add_column('api_keys', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Add description column (optional)
    op.add_column('api_keys', sa.Column('description', sa.Text(), nullable=True))

    # Add badge_public column (default False)
    op.add_column('api_keys', sa.Column('badge_public', sa.Boolean(), nullable=False, server_default='false'))

    # Add badge_uuid column (unique identifier for badge access)
    op.add_column('api_keys', sa.Column('badge_uuid', postgresql.UUID(as_uuid=True), nullable=True))

    # Create unique index on badge_uuid
    op.create_index(op.f('ix_api_keys_badge_uuid'), 'api_keys', ['badge_uuid'], unique=True)


def downgrade() -> None:
    """Remove is_active, description, badge_public, and badge_uuid columns from api_keys table."""
    op.drop_index(op.f('ix_api_keys_badge_uuid'), table_name='api_keys')
    op.drop_column('api_keys', 'badge_uuid')
    op.drop_column('api_keys', 'badge_public')
    op.drop_column('api_keys', 'description')
    op.drop_column('api_keys', 'is_active')
