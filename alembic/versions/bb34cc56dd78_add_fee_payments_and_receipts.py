"""Add fee payments + receipt counters

Revision ID: bb34cc56dd78
Revises: aa12bb34cc56
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "bb34cc56dd78"
down_revision = "aa12bb34cc56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fee_receipt_counters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("next_seq", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("school_id", "year", name="uq_fee_receipt_counters_school_year"),
    )
    op.create_index("ix_fee_receipt_counters_school_id", "fee_receipt_counters", ["school_id"])
    op.create_index("ix_fee_receipt_counters_year", "fee_receipt_counters", ["year"])

    op.create_table(
        "fee_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fee_structure_id", sa.Integer(), sa.ForeignKey("fee_structures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session", sa.String(length=16), nullable=False),
        sa.Column("amount_paid", sa.Integer(), nullable=False),
        sa.Column("payment_mode", sa.String(length=20), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt_number", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("school_id", "receipt_number", name="uq_fee_payments_school_receipt_number"),
    )
    op.create_index("ix_fee_payments_school_id", "fee_payments", ["school_id"])
    op.create_index("ix_fee_payments_student_id", "fee_payments", ["student_id"])
    op.create_index("ix_fee_payments_fee_structure_id", "fee_payments", ["fee_structure_id"])
    op.create_index("ix_fee_payments_session", "fee_payments", ["session"])
    op.create_index("ix_fee_payments_payment_date", "fee_payments", ["payment_date"])
    op.create_index("ix_fee_payments_receipt_number", "fee_payments", ["receipt_number"])
    op.create_index("ix_fee_payments_recorded_by_user_id", "fee_payments", ["recorded_by_user_id"])

    op.create_table(
        "fee_payment_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("fee_payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fee_head_id", sa.Integer(), sa.ForeignKey("fee_heads.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("payment_id", "fee_head_id", name="uq_fee_payment_items_payment_head"),
    )
    op.create_index("ix_fee_payment_items_payment_id", "fee_payment_items", ["payment_id"])
    op.create_index("ix_fee_payment_items_fee_head_id", "fee_payment_items", ["fee_head_id"])


def downgrade() -> None:
    op.drop_index("ix_fee_payment_items_fee_head_id", table_name="fee_payment_items")
    op.drop_index("ix_fee_payment_items_payment_id", table_name="fee_payment_items")
    op.drop_table("fee_payment_items")

    op.drop_index("ix_fee_payments_recorded_by_user_id", table_name="fee_payments")
    op.drop_index("ix_fee_payments_receipt_number", table_name="fee_payments")
    op.drop_index("ix_fee_payments_payment_date", table_name="fee_payments")
    op.drop_index("ix_fee_payments_session", table_name="fee_payments")
    op.drop_index("ix_fee_payments_fee_structure_id", table_name="fee_payments")
    op.drop_index("ix_fee_payments_student_id", table_name="fee_payments")
    op.drop_index("ix_fee_payments_school_id", table_name="fee_payments")
    op.drop_table("fee_payments")

    op.drop_index("ix_fee_receipt_counters_year", table_name="fee_receipt_counters")
    op.drop_index("ix_fee_receipt_counters_school_id", table_name="fee_receipt_counters")
    op.drop_table("fee_receipt_counters")

