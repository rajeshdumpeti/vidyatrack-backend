"""create principals table

Revision ID: 860e577da006
Revises: 76e77b2d85a9
Create Date: 2026-01-16 01:13:41.423706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '860e577da006'
down_revision: Union[str, None] = '76e77b2d85a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "principals",
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
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Exactly ONE principal per school
    op.create_unique_constraint(
        "uq_principals_school_id",
        "principals",
        ["school_id"],
    )

    # Optional but recommended: one principal per user
    op.create_unique_constraint(
        "uq_principals_user_id",
        "principals",
        ["user_id"],
    )

    op.create_index(
        "ix_principals_school_id",
        "principals",
        ["school_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_principals_school_id", table_name="principals")
    op.drop_constraint("uq_principals_user_id", "principals", type_="unique")
    op.drop_constraint("uq_principals_school_id", "principals", type_="unique")
    op.drop_table("principals")
