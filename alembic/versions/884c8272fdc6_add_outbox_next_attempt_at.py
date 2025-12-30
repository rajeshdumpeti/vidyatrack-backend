"""add outbox next_attempt_at

Revision ID: 884c8272fdc6
Revises: 9ece9554bba5
Create Date: 2025-12-29 17:47:42.037532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '884c8272fdc6'
down_revision: Union[str, None] = '9ece9554bba5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_outbox_attendance_event_submission_recipient",
        "notification_outbox",
        ["event_type", "attendance_submission_id", "recipient_phone"],
        unique=True,
        postgresql_where=sa.text("attendance_submission_id IS NOT NULL"),
    )

    op.create_index(
        "uq_outbox_marks_event_submission_recipient",
        "notification_outbox",
        ["event_type", "marks_submission_id", "recipient_phone"],
        unique=True,
        postgresql_where=sa.text("marks_submission_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_outbox_marks_event_submission_recipient",
                  table_name="notification_outbox")
    op.drop_index("uq_outbox_attendance_event_submission_recipient",
                  table_name="notification_outbox")
