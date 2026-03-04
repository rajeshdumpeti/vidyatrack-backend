"""restore principals table if missing

Revision ID: 6f4a1e2c9b7d
Revises: e7a1b4c9d2f0
Create Date: 2026-03-03 21:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f4a1e2c9b7d"
down_revision: Union[str, None] = "e7a1b4c9d2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("principals"):
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

    # Ensure unique constraints and index exist even if table was partially created.
    inspector = sa.inspect(bind)
    unique_names = {u["name"] for u in inspector.get_unique_constraints("principals")}
    index_names = {i["name"] for i in inspector.get_indexes("principals")}

    if "uq_principals_school_id" not in unique_names:
        op.create_unique_constraint(
            "uq_principals_school_id",
            "principals",
            ["school_id"],
        )
    if "uq_principals_user_id" not in unique_names:
        op.create_unique_constraint(
            "uq_principals_user_id",
            "principals",
            ["user_id"],
        )
    if "ix_principals_school_id" not in index_names:
        op.create_index(
            "ix_principals_school_id",
            "principals",
            ["school_id"],
        )


def downgrade() -> None:
    # No-op by design: this is a schema repair migration.
    pass

