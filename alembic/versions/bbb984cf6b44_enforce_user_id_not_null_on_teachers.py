"""enforce user_id not null on teachers

Revision ID: bbb984cf6b44
Revises: f83557209d5e
Create Date: 2025-12-30 16:27:36.474828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbb984cf6b44'
down_revision: Union[str, None] = 'f83557209d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "teachers",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    # DO NOT create uq_teachers_user_id here because it already exists
    # from migration f83557209d5e


def downgrade() -> None:
    op.alter_column(
        "teachers",
        "user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    # DO NOT drop uq_teachers_user_id / FK / column here.
    # Those belong to f83557209d5e, not this migration.
