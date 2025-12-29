"""add attendance indexes

Revision ID: a7fd0e240560
Revises: e0154ef0f1a9
Create Date: 2025-12-29 13:42:49.626153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7fd0e240560'
down_revision: Union[str, None] = 'e0154ef0f1a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_attendance_school_date", "attendance_records", [
                    "school_id", "date"], unique=False)
    op.create_index("ix_attendance_school_student", "attendance_records", [
        "school_id", "student_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_attendance_school_student",
                  table_name="attendance_records")
    op.drop_index("ix_attendance_school_date", table_name="attendance_records")
