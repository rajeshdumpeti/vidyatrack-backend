"""add email to users

Revision ID: 61421bb28be5
Revises: c4b1f0a1b2cd
Create Date: 2026-01-15 00:46:09.979610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61421bb28be5'
down_revision: Union[str, None] = 'c4b1f0a1b2cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column(
        "email", sa.String(length=255), nullable=True))
    op.create_index("ix_users_email", "users", ["email"])

    # Optional but recommended for idempotency safety:
    # unique per school when email is present (partial unique index)
    op.create_index(
        "uq_users_school_email",
        "users",
        ["school_id", "email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_school_email", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")
