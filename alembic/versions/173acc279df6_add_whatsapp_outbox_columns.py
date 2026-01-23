"""add_whatsapp_outbox_columns

Revision ID: 173acc279df6
Revises: 026034bac710
Create Date: 2026-01-20 01:02:21.281709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '173acc279df6'
down_revision: Union[str, None] = '026034bac710'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("notification_outbox") as batch:
        batch.add_column(sa.Column("provider", sa.String(32), nullable=True))
        batch.add_column(sa.Column("provider_message_id",
                         sa.String(255), nullable=True))
        batch.add_column(sa.Column("last_error_code",
                         sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("last_error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("notification_outbox") as batch:
        batch.drop_column("last_error_message")
        batch.drop_column("last_error_code")
        batch.drop_column("provider_message_id")
        batch.drop_column("provider")
