"""add students section_id

Revision ID: 9ece9554bba5
Revises: 4d1b0b81d2b9
Create Date: 2025-12-29 16:56:29.001995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ece9554bba5'
down_revision: Union[str, None] = '4d1b0b81d2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("section_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_students_section_id_sections",
        "students",
        "sections",
        ["section_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_students_section_id",
        "students",
        ["section_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_students_section_id", table_name="students")
    op.drop_constraint("fk_students_section_id_sections",
                       "students", type_="foreignkey")
    op.drop_column("students", "section_id")
