"""user_school: add is_active + unique constraint per (user, school, role)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-26 00:00:00.000000

Why:
  Previously one user could only have one role per school. This change
  enables the same person (e.g. a principal who also teaches) to hold
  multiple roles at the same school without conflicts.
"""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add is_active column (defaults to True for all existing rows)
    op.add_column(
        "user_schools",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )

    # 2. Remove any duplicate (user_id, school_id) rows — keep the oldest.
    #    In practice there should be none, but we guard against it before
    #    adding the unique constraint.
    op.execute("""
        DELETE FROM user_schools
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM user_schools
            GROUP BY user_id, school_id, role
        )
    """)

    # 3. Add unique constraint on (user_id, school_id, role)
    op.create_unique_constraint(
        "uq_user_school_role",
        "user_schools",
        ["user_id", "school_id", "role"],
    )

    # 4. Add indexes for fast lookups
    op.create_index("ix_user_schools_user_id", "user_schools", ["user_id"])
    op.create_index("ix_user_schools_school_id", "user_schools", ["school_id"])


def downgrade() -> None:
    op.drop_index("ix_user_schools_school_id", table_name="user_schools")
    op.drop_index("ix_user_schools_user_id", table_name="user_schools")
    op.drop_constraint("uq_user_school_role", "user_schools", type_="unique")
    op.drop_column("user_schools", "is_active")
