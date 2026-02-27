"""add whatsapp delivery fields to otp_requests

Revision ID: c2e5d3f4a8b1
Revises: 1b6c2bdf6b1e
Create Date: 2026-02-21 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2e5d3f4a8b1"
down_revision: Union[str, None] = "1b6c2bdf6b1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "otp_requests",
        sa.Column("channel", sa.String(length=16), server_default="WHATSAPP", nullable=False),
    )
    op.add_column("otp_requests", sa.Column("provider_message_id", sa.String(length=255), nullable=True))
    op.add_column(
        "otp_requests",
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
    )
    op.add_column(
        "otp_requests",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("otp_requests", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(
        "ix_otp_requests_phone_created_at_desc",
        "otp_requests",
        ["phone", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_otp_requests_phone_status", "otp_requests", ["phone", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_otp_requests_phone_status", table_name="otp_requests")
    op.drop_index("ix_otp_requests_phone_created_at_desc", table_name="otp_requests")
    op.drop_column("otp_requests", "sent_at")
    op.drop_column("otp_requests", "attempts")
    op.drop_column("otp_requests", "status")
    op.drop_column("otp_requests", "provider_message_id")
    op.drop_column("otp_requests", "channel")
