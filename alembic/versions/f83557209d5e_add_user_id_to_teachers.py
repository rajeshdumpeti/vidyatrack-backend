"""add user_id to teachers

Revision ID: f83557209d5e
Revises: e20cba61afbe
Create Date: 2025-12-30 15:56:28.655711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f83557209d5e'
down_revision: Union[str, None] = 'e20cba61afbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column as nullable FIRST
    op.add_column(
        "teachers",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )

    # 2. Add FK (still nullable is OK)
    op.create_foreign_key(
        "fk_teachers_user_id",
        "teachers",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("uq_teachers_user_id", "teachers", type_="unique")
    op.drop_constraint("fk_teachers_user_id", "teachers", type_="foreignkey")
    op.drop_column("teachers", "user_id")
