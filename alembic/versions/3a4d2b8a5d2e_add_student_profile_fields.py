"""add student profile fields

Revision ID: 3a4d2b8a5d2e
Revises: 4d1b0b81d2b9
Create Date: 2026-01-19 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "3a4d2b8a5d2e"
down_revision = "4d1b0b81d2b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("students", sa.Column("gender", sa.String(length=16), nullable=True))
    op.add_column("students", sa.Column("roll_number", sa.String(length=32), nullable=True))
    op.add_column("students", sa.Column("admission_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("students", "admission_date")
    op.drop_column("students", "roll_number")
    op.drop_column("students", "gender")
    op.drop_column("students", "date_of_birth")
    op.drop_column("students", "last_name")
    op.drop_column("students", "first_name")
