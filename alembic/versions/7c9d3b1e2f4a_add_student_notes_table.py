"""add student_notes table

Revision ID: 7c9d3b1e2f4a
Revises: 5b7c1f1b2c3e
Create Date: 2026-03-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7c9d3b1e2f4a"
down_revision = "5b7c1f1b2c3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.has_table(conn, "student_notes"):
        return

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
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_student_notes_school_id"), "student_notes", ["school_id"], unique=False)
    op.create_index(op.f("ix_student_notes_student_id"), "student_notes", ["student_id"], unique=False)
    op.create_index(op.f("ix_student_notes_author_user_id"), "student_notes", ["author_user_id"], unique=False)
    op.create_index(
        "ix_student_notes_school_student",
        "student_notes",
        ["school_id", "student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_student_notes_school_student", table_name="student_notes")
    op.drop_index(op.f("ix_student_notes_author_user_id"), table_name="student_notes")
    op.drop_index(op.f("ix_student_notes_student_id"), table_name="student_notes")
    op.drop_index(op.f("ix_student_notes_school_id"), table_name="student_notes")
    op.drop_table("student_notes")
