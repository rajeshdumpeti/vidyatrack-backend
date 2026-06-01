"""add management prd admission and payroll

Revision ID: e6f7a8b9c0d1
Revises: d4f5e6a7b8c9
Create Date: 2026-04-05 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e6f7a8b9c0d1"
down_revision = "d4f5e6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"))
    op.add_column("students", sa.Column("academic_year", sa.String(length=32), nullable=True))
    op.add_column("students", sa.Column("admission_number", sa.String(length=64), nullable=True))
    op.add_column("students", sa.Column("blood_group", sa.String(length=8), nullable=True))
    op.add_column("students", sa.Column("nationality", sa.String(length=64), nullable=True))
    op.add_column("students", sa.Column("religion", sa.String(length=64), nullable=True))
    op.add_column("students", sa.Column("caste_category", sa.String(length=32), nullable=True))
    op.add_column("students", sa.Column("mother_tongue", sa.String(length=64), nullable=True))
    op.add_column("students", sa.Column("aadhaar_number", sa.String(length=255), nullable=True))
    op.add_column("students", sa.Column("birth_cert_number", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("previous_school_name", sa.String(length=200), nullable=True))
    op.add_column("students", sa.Column("previous_school_tc_number", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("students", sa.Column("emergency_contact_name", sa.String(length=200), nullable=True))
    op.add_column("students", sa.Column("emergency_contact_relation", sa.String(length=64), nullable=True))
    op.add_column("students", sa.Column("emergency_contact_phone", sa.String(length=32), nullable=True))

    op.create_table(
        "staff_compensation_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("employment_type", sa.String(length=32), nullable=False, server_default="permanent"),
        sa.Column("gross_salary", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("payment_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payment_mode", sa.String(length=32), nullable=False, server_default="bank_transfer"),
        sa.Column("date_of_joining", sa.Date(), nullable=True),
        sa.Column("contract_end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "user_id", name="uq_staff_compensation_school_user"),
    )
    op.create_index(op.f("ix_staff_compensation_profiles_id"), "staff_compensation_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_staff_compensation_profiles_school_id"), "staff_compensation_profiles", ["school_id"], unique=False)
    op.create_index(op.f("ix_staff_compensation_profiles_user_id"), "staff_compensation_profiles", ["user_id"], unique=False)

    op.create_table(
        "staff_payroll_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("payroll_month", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_mode", sa.String(length=32), nullable=False, server_default="bank_transfer"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PAID"),
        sa.Column("reference_note", sa.String(length=255), nullable=True),
        sa.Column("processed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["processed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "user_id", "payroll_month", name="uq_staff_payroll_school_user_month"),
    )
    op.create_index(op.f("ix_staff_payroll_records_id"), "staff_payroll_records", ["id"], unique=False)
    op.create_index(op.f("ix_staff_payroll_records_school_id"), "staff_payroll_records", ["school_id"], unique=False)
    op.create_index(op.f("ix_staff_payroll_records_user_id"), "staff_payroll_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_staff_payroll_records_payroll_month"), "staff_payroll_records", ["payroll_month"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_staff_payroll_records_payroll_month"), table_name="staff_payroll_records")
    op.drop_index(op.f("ix_staff_payroll_records_user_id"), table_name="staff_payroll_records")
    op.drop_index(op.f("ix_staff_payroll_records_school_id"), table_name="staff_payroll_records")
    op.drop_index(op.f("ix_staff_payroll_records_id"), table_name="staff_payroll_records")
    op.drop_table("staff_payroll_records")

    op.drop_index(op.f("ix_staff_compensation_profiles_user_id"), table_name="staff_compensation_profiles")
    op.drop_index(op.f("ix_staff_compensation_profiles_school_id"), table_name="staff_compensation_profiles")
    op.drop_index(op.f("ix_staff_compensation_profiles_id"), table_name="staff_compensation_profiles")
    op.drop_table("staff_compensation_profiles")

    for column in [
        "emergency_contact_phone",
        "emergency_contact_relation",
        "emergency_contact_name",
        "address",
        "previous_school_tc_number",
        "previous_school_name",
        "birth_cert_number",
        "aadhaar_number",
        "mother_tongue",
        "caste_category",
        "religion",
        "nationality",
        "blood_group",
        "admission_number",
        "academic_year",
        "status",
    ]:
        op.drop_column("students", column)
