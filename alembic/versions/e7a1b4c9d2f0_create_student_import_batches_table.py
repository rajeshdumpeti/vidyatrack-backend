"""create student import batches table

Revision ID: e7a1b4c9d2f0
Revises: c2e5d3f4a8b1
Create Date: 2026-02-27 15:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7a1b4c9d2f0"
down_revision: Union[str, None] = "c2e5d3f4a8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_import_batches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("is_committed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_student_import_batches_id"),
        "student_import_batches",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_import_batches_school_id"),
        "student_import_batches",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_import_batches_user_id"),
        "student_import_batches",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_student_import_batches_user_id"), table_name="student_import_batches")
    op.drop_index(op.f("ix_student_import_batches_school_id"), table_name="student_import_batches")
    op.drop_index(op.f("ix_student_import_batches_id"), table_name="student_import_batches")
    op.drop_table("student_import_batches")
