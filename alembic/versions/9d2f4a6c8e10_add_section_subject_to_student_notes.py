"""add section and subject to student_notes

Revision ID: 9d2f4a6c8e10
Revises: 7c9d3b1e2f4a
Create Date: 2026-03-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9d2f4a6c8e10"
down_revision = "7c9d3b1e2f4a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if not conn.dialect.has_table(conn, "student_notes"):
        return

    op.add_column("student_notes", sa.Column("section_id", sa.Integer(), nullable=True))
    op.add_column("student_notes", sa.Column("subject_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_student_notes_section_id"), "student_notes", ["section_id"], unique=False)
    op.create_index(op.f("ix_student_notes_subject_id"), "student_notes", ["subject_id"], unique=False)
    op.create_foreign_key(
        "fk_student_notes_section_id",
        "student_notes",
        "sections",
        ["section_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_student_notes_subject_id",
        "student_notes",
        "subjects",
        ["subject_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_student_notes_subject_id", "student_notes", type_="foreignkey")
    op.drop_constraint("fk_student_notes_section_id", "student_notes", type_="foreignkey")
    op.drop_index(op.f("ix_student_notes_subject_id"), table_name="student_notes")
    op.drop_index(op.f("ix_student_notes_section_id"), table_name="student_notes")
    op.drop_column("student_notes", "subject_id")
    op.drop_column("student_notes", "section_id")
