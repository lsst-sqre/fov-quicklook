"""add_cache_version_to_quicklooks

Revision ID: a44e31783f90
Revises: 8611afc3febd
Create Date: 2026-05-26 18:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a44e31783f90'
down_revision: Union[str, Sequence[str], None] = '8611afc3febd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'quicklooks',
        sa.Column('cache_version', sa.Integer(), nullable=False, server_default='1'),
    )
    op.alter_column('quicklooks', 'cache_version', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('quicklooks', 'cache_version')
