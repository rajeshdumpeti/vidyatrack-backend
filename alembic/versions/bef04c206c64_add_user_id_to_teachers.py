"""add user_id to teachers

Revision ID: bef04c206c64
Revises: 0cfca8bbc912
Create Date: 2026-01-10 15:15:02.688716

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bef04c206c64'
down_revision: Union[str, None] = '0cfca8bbc912'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
