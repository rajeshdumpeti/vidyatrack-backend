"""add email to users

Revision ID: 76e77b2d85a9
Revises: 61421bb28be5
Create Date: 2026-01-15 00:56:26.922750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76e77b2d85a9'
down_revision: Union[str, None] = '61421bb28be5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
