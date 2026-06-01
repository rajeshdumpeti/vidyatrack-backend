"""add management setup option a

Revision ID: c1d2e3f4a5b6
Revises: bb34cc56dd78
Create Date: 2026-04-05 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "bb34cc56dd78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "schools",
        sa.Column("management_setup_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "schools",
        sa.Column("management_setup_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sections",
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="40"),
    )
    op.add_column(
        "sections",
        sa.Column("room_number", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "sections",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "class_subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("internal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("subject_type", sa.String(length=24), nullable=False, server_default="core"),
        sa.Column("max_marks", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("passing_marks", sa.Integer(), nullable=False, server_default="35"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("internal_id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint(
            "school_id",
            "class_id",
            "subject_id",
            name="uq_class_subjects_school_class_subject",
        ),
    )
    op.create_index(op.f("ix_class_subjects_id"), "class_subjects", ["id"], unique=False)
    op.create_index(op.f("ix_class_subjects_school_id"), "class_subjects", ["school_id"], unique=False)
    op.create_index(op.f("ix_class_subjects_class_id"), "class_subjects", ["class_id"], unique=False)
    op.create_index(op.f("ix_class_subjects_subject_id"), "class_subjects", ["subject_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_class_subjects_subject_id"), table_name="class_subjects")
    op.drop_index(op.f("ix_class_subjects_class_id"), table_name="class_subjects")
    op.drop_index(op.f("ix_class_subjects_school_id"), table_name="class_subjects")
    op.drop_index(op.f("ix_class_subjects_id"), table_name="class_subjects")
    op.drop_table("class_subjects")
    op.drop_column("sections", "is_active")
    op.drop_column("sections", "room_number")
    op.drop_column("sections", "capacity")
    op.drop_column("schools", "management_setup_completed_at")
    op.drop_column("schools", "management_setup_complete")
