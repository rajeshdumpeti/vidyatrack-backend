"""Add fees MVP tables

Revision ID: aa12bb34cc56
Revises: a3c1d9e8b7f2
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "aa12bb34cc56"
down_revision = "a3c1d9e8b7f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fee_heads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=24), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("school_id", "code", name="uq_fee_heads_school_code"),
    )
    op.create_index("ix_fee_heads_school_id", "fee_heads", ["school_id"])

    op.create_table(
        "fee_structures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("session", sa.String(length=16), nullable=False),
        sa.Column("grade_name", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("school_id", "session", "grade_name", name="uq_fee_structures_school_session_grade"),
    )
    op.create_index("ix_fee_structures_school_id", "fee_structures", ["school_id"])
    op.create_index("ix_fee_structures_session", "fee_structures", ["session"])
    op.create_index("ix_fee_structures_grade_name", "fee_structures", ["grade_name"])

    op.create_table(
        "fee_structure_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fee_structure_id", sa.Integer(), sa.ForeignKey("fee_structures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fee_head_id", sa.Integer(), sa.ForeignKey("fee_heads.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("fee_structure_id", "fee_head_id", name="uq_fee_structure_items_structure_head"),
    )
    op.create_index("ix_fee_structure_items_fee_structure_id", "fee_structure_items", ["fee_structure_id"])
    op.create_index("ix_fee_structure_items_fee_head_id", "fee_structure_items", ["fee_head_id"])


def downgrade() -> None:
    op.drop_index("ix_fee_structure_items_fee_head_id", table_name="fee_structure_items")
    op.drop_index("ix_fee_structure_items_fee_structure_id", table_name="fee_structure_items")
    op.drop_table("fee_structure_items")

    op.drop_index("ix_fee_structures_grade_name", table_name="fee_structures")
    op.drop_index("ix_fee_structures_session", table_name="fee_structures")
    op.drop_index("ix_fee_structures_school_id", table_name="fee_structures")
    op.drop_table("fee_structures")

    op.drop_index("ix_fee_heads_school_id", table_name="fee_heads")
    op.drop_table("fee_heads")

