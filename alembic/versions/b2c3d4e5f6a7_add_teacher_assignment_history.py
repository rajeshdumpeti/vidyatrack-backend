"""add teacher_assignment_history table

Revision ID: b2c3d4e5f6a7
Revises: 9d2f4a6c8e10
Create Date: 2026-03-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "1f2a3b4c5d6e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teacher_assignment_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("previous_teacher_id", sa.Integer(), nullable=True),
        sa.Column("new_teacher_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["previous_teacher_id"], ["teachers.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["new_teacher_id"], ["teachers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teacher_assignment_history_id"), "teacher_assignment_history", ["id"], unique=False)
    op.create_index("ix_tah_school_section_subject", "teacher_assignment_history", ["school_id", "section_id", "subject_id"], unique=False)
    op.create_index("ix_tah_changed_at", "teacher_assignment_history", ["changed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tah_changed_at", table_name="teacher_assignment_history")
    op.drop_index("ix_tah_school_section_subject", table_name="teacher_assignment_history")
    op.drop_index(op.f("ix_teacher_assignment_history_id"), table_name="teacher_assignment_history")
    op.drop_table("teacher_assignment_history")
