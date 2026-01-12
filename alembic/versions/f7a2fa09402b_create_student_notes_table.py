"""create student_notes table

Revision ID: f7a2fa09402b
Revises: bef04c206c64
Create Date: 2026-01-12 16:32:06.353572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a2fa09402b'
down_revision: Union[str, None] = 'bef04c206c64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )

    op.create_index(
        "ix_student_notes_school_student",
        "student_notes",
        ["school_id", "student_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_notes_school_student",
                  table_name="student_notes")
    op.drop_table("student_notes")
