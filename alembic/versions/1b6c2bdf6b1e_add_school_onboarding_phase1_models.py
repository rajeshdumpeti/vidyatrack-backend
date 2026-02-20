"""add school onboarding phase1 models

Revision ID: 1b6c2bdf6b1e
Revises: 9e2a5b6f4c1d
Create Date: 2026-02-19 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1b6c2bdf6b1e"
down_revision: Union[str, None] = "9e2a5b6f4c1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("can_create_school", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("max_schools", sa.Integer(), nullable=True))

    op.add_column("schools", sa.Column("code", sa.String(length=64), nullable=True))
    op.add_column("schools", sa.Column("board", sa.String(length=64), nullable=True))
    op.add_column("schools", sa.Column("category", sa.String(length=64), nullable=True))
    op.add_column("schools", sa.Column("medium", sa.String(length=64), nullable=True))
    op.add_column("schools", sa.Column("school_type", sa.String(length=64), nullable=True))
    op.add_column("schools", sa.Column("established_year", sa.Integer(), nullable=True))
    op.add_column("schools", sa.Column("affiliation_number", sa.String(length=64), nullable=True))
    op.add_column("schools", sa.Column("udise_code", sa.String(length=32), nullable=True))
    op.add_column("schools", sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"))
    op.add_column("schools", sa.Column("created_by", sa.Integer(), nullable=True))
    op.add_column("schools", sa.Column("updated_by", sa.Integer(), nullable=True))
    op.add_column(
        "schools",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "schools",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )

    op.create_index("ix_schools_code", "schools", ["code"], unique=True)
    op.create_index("ix_schools_udise_code", "schools", ["udise_code"], unique=True)

    op.create_foreign_key("fk_schools_created_by_users", "schools", "users", ["created_by"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_schools_updated_by_users", "schools", "users", ["updated_by"], ["id"], ondelete="SET NULL")

    op.create_table(
        "school_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("area", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("district", sa.String(length=128), nullable=True),
        sa.Column("state", sa.String(length=128), nullable=True),
        sa.Column("pin_code", sa.String(length=12), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("landmark", sa.String(length=255), nullable=True),
        sa.Column("school_phone", sa.String(length=20), nullable=True),
        sa.Column("school_email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", name="uq_school_contacts_school_id"),
        sa.UniqueConstraint("school_email", name="uq_school_contacts_school_email"),
    )
    op.create_index("ix_school_contacts_school_id", "school_contacts", ["school_id"], unique=False)

    op.create_table(
        "school_academic_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("current_session", sa.String(length=64), nullable=True),
        sa.Column("academic_start_month", sa.Integer(), nullable=True),
        sa.Column("academic_end_month", sa.Integer(), nullable=True),
        sa.Column("working_days_per_week", sa.Integer(), nullable=True),
        sa.Column("class_levels", sa.JSON(), nullable=True),
        sa.Column("lkg_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ukg_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pre_nursery_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", name="uq_school_academic_details_school_id"),
    )
    op.create_index("ix_school_academic_details_school_id", "school_academic_details", ["school_id"], unique=False)

    op.create_table(
        "school_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("modules_enabled", sa.JSON(), nullable=True),
        sa.Column("max_students", sa.Integer(), nullable=True),
        sa.Column("max_teachers", sa.Integer(), nullable=True),
        sa.Column("max_staff", sa.Integer(), nullable=True),
        sa.Column("storage_limit_gb", sa.Integer(), nullable=True),
        sa.Column("api_access", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bulk_operations", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("custom_reports", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", name="uq_school_features_school_id"),
    )
    op.create_index("ix_school_features_school_id", "school_features", ["school_id"], unique=False)

    op.create_table(
        "management_admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("designation", sa.String(length=100), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("employee_id", sa.String(length=64), nullable=True),
        sa.Column("language_preference", sa.String(length=32), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "user_id", name="uq_management_admin_school_user"),
    )
    op.create_index("ix_management_admins_school_id", "management_admins", ["school_id"], unique=False)
    op.create_index("ix_management_admins_user_id", "management_admins", ["user_id"], unique=False)

    op.create_table(
        "school_onboarding_drafts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_school_onboarding_drafts_id", "school_onboarding_drafts", ["id"], unique=False)

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "scope", "key", name="uq_idempotency_user_scope_key"),
    )
    op.create_index("ix_idempotency_keys_user_id", "idempotency_keys", ["user_id"], unique=False)
    op.create_index("ix_idempotency_keys_scope", "idempotency_keys", ["scope"], unique=False)



def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_scope", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_user_id", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    op.drop_index("ix_school_onboarding_drafts_id", table_name="school_onboarding_drafts")
    op.drop_table("school_onboarding_drafts")

    op.drop_index("ix_management_admins_user_id", table_name="management_admins")
    op.drop_index("ix_management_admins_school_id", table_name="management_admins")
    op.drop_table("management_admins")

    op.drop_index("ix_school_features_school_id", table_name="school_features")
    op.drop_table("school_features")

    op.drop_index("ix_school_academic_details_school_id", table_name="school_academic_details")
    op.drop_table("school_academic_details")

    op.drop_index("ix_school_contacts_school_id", table_name="school_contacts")
    op.drop_table("school_contacts")

    op.drop_constraint("fk_schools_updated_by_users", "schools", type_="foreignkey")
    op.drop_constraint("fk_schools_created_by_users", "schools", type_="foreignkey")
    op.drop_index("ix_schools_udise_code", table_name="schools")
    op.drop_index("ix_schools_code", table_name="schools")

    op.drop_column("schools", "updated_at")
    op.drop_column("schools", "created_at")
    op.drop_column("schools", "updated_by")
    op.drop_column("schools", "created_by")
    op.drop_column("schools", "status")
    op.drop_column("schools", "udise_code")
    op.drop_column("schools", "affiliation_number")
    op.drop_column("schools", "established_year")
    op.drop_column("schools", "school_type")
    op.drop_column("schools", "medium")
    op.drop_column("schools", "category")
    op.drop_column("schools", "board")
    op.drop_column("schools", "code")

    op.drop_column("users", "max_schools")
    op.drop_column("users", "can_create_school")
