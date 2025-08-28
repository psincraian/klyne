"""add_free_plan_support

Revision ID: 25612c4a60e2
Revises: e19160229bb6
Create Date: 2025-08-28 21:34:31.878780

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '25612c4a60e2'
down_revision: Union[str, Sequence[str], None] = 'e19160229bb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support free plan defaults."""
    # Set default values for new users to have free plan
    op.alter_column('users', 'subscription_tier', 
                   server_default="'free'")
    op.alter_column('users', 'subscription_status', 
                   server_default="'active'")
    
    # Update existing users without subscription_tier to free plan
    op.execute("UPDATE users SET subscription_tier = 'free' WHERE subscription_tier IS NULL")
    op.execute("UPDATE users SET subscription_status = 'active' WHERE subscription_status IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove default values from user columns
    op.alter_column('users', 'subscription_tier', 
                   server_default=None)
    op.alter_column('users', 'subscription_status', 
                   server_default=None)
