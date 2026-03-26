"""add substitute_teacher_id to section_subject_teachers

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "section_subject_teachers",
        sa.Column(
            "substitute_teacher_id",
            sa.Integer(),
            sa.ForeignKey("teachers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_sst_substitute_teacher",
        "section_subject_teachers",
        ["substitute_teacher_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_sst_substitute_teacher", table_name="section_subject_teachers")
    op.drop_column("section_subject_teachers", "substitute_teacher_id")
