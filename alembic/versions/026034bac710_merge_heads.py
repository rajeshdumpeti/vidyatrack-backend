"""merge heads

Revision ID: 026034bac710
Revises: 3a4d2b8a5d2e, 860e577da006
Create Date: 2026-01-19 02:16:10.078912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '026034bac710'
down_revision: Union[str, None] = ('3a4d2b8a5d2e', '860e577da006')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
