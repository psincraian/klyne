"""Merge migration heads

Revision ID: 9a1573a14fb8
Revises: 8d864487834a, f0815de6fe96
Create Date: 2025-08-15 22:02:06.558569

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '9a1573a14fb8'
down_revision: Union[str, Sequence[str], None] = ('8d864487834a', 'f0815de6fe96')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
