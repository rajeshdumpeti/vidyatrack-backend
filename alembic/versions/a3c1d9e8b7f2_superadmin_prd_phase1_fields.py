"""superadmin PRD phase1 fields: school plan/test/suspension, contact lat/lng, user internal uuid, school_grades

Revision ID: a3c1d9e8b7f2
Revises: f6a7b8c9d1e2
Create Date: 2026-04-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a3c1d9e8b7f2"
down_revision = "f6a7b8c9d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.add_column(
        "users",
        sa.Column(
            "internal_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_unique_constraint("uq_users_internal_id", "users", ["internal_id"])

    # --- schools ---
    op.add_column("schools", sa.Column("plan_type", sa.String(32), nullable=False, server_default="pilot"))
    op.add_column("schools", sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("schools", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("schools", sa.Column("billing_starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("schools", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("schools", sa.Column("suspension_reason", sa.String(512), nullable=True))

    # --- school_contacts ---
    op.add_column("school_contacts", sa.Column("latitude", sa.Numeric(10, 8), nullable=True))
    op.add_column("school_contacts", sa.Column("longitude", sa.Numeric(11, 8), nullable=True))

    # --- school_grades ---
    op.create_table(
        "school_grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "school_id",
            sa.Integer(),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("grade_name", sa.String(50), nullable=False),
        sa.Column("grade_code", sa.String(20), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_school_grades_school_grade_code", "school_grades", ["school_id", "grade_code"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_school_grades_school_grade_code", "school_grades", type_="unique")
    op.drop_table("school_grades")

    op.drop_column("school_contacts", "longitude")
    op.drop_column("school_contacts", "latitude")

    op.drop_column("schools", "suspension_reason")
    op.drop_column("schools", "suspended_at")
    op.drop_column("schools", "billing_starts_at")
    op.drop_column("schools", "trial_ends_at")
    op.drop_column("schools", "is_test")
    op.drop_column("schools", "plan_type")

    op.drop_constraint("uq_users_internal_id", "users", type_="unique")
    op.drop_column("users", "internal_id")
