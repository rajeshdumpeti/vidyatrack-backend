"""add principal onboarding and history tables

Revision ID: 9a1f0b3c7d4e
Revises: 6f4a1e2c9b7d
Create Date: 2026-03-03 22:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a1f0b3c7d4e"
down_revision: Union[str, None] = "6f4a1e2c9b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "principal_onboarding_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "school_id",
            sa.Integer(),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_principal_onboarding_sessions_school_id",
        "principal_onboarding_sessions",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        "ix_principal_onboarding_sessions_requested_by_user_id",
        "principal_onboarding_sessions",
        ["requested_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_principal_onboarding_sessions_phone",
        "principal_onboarding_sessions",
        ["phone"],
        unique=False,
    )

    op.create_table(
        "principal_assignment_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "school_id",
            sa.Integer(),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "replaced_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_principal_assignment_history_school_id",
        "principal_assignment_history",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        "ix_principal_assignment_history_user_id",
        "principal_assignment_history",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_principal_assignment_history_replaced_by_user_id",
        "principal_assignment_history",
        ["replaced_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_principal_assignment_history_status",
        "principal_assignment_history",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_principal_assignment_history_status",
        table_name="principal_assignment_history",
    )
    op.drop_index(
        "ix_principal_assignment_history_replaced_by_user_id",
        table_name="principal_assignment_history",
    )
    op.drop_index(
        "ix_principal_assignment_history_user_id",
        table_name="principal_assignment_history",
    )
    op.drop_index(
        "ix_principal_assignment_history_school_id",
        table_name="principal_assignment_history",
    )
    op.drop_table("principal_assignment_history")

    op.drop_index(
        "ix_principal_onboarding_sessions_phone",
        table_name="principal_onboarding_sessions",
    )
    op.drop_index(
        "ix_principal_onboarding_sessions_requested_by_user_id",
        table_name="principal_onboarding_sessions",
    )
    op.drop_index(
        "ix_principal_onboarding_sessions_school_id",
        table_name="principal_onboarding_sessions",
    )
    op.drop_table("principal_onboarding_sessions")
