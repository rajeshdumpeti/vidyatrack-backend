from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.notification_outbox import NotificationOutbox


def process_outbox_batch(
    db: Session,
    *,
    limit: int = 50,
) -> int:
    """
    Phase 2 worker (synchronous, local-run only):
    - Fetch PENDING outbox rows
    - 'Send' by printing to console (no external integration)
    - Mark row SENT with sent_at
    - Retry-safe: if a row is already SENT, it will not be reprocessed
    """
    rows = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.status == "PENDING")
        .order_by(NotificationOutbox.id.asc())
        .limit(limit)
        .all()
    )

    processed = 0
    now = datetime.now(timezone.utc)

    for row in rows:
        # Simulated send: console output only
        print(
            f"[OUTBOX][SEND] id={row.id} event={row.event_type} "
            f"to={row.recipient_phone} payload={row.payload}"
        )

        row.status = "SENT"
        row.sent_at = now
        row.last_error = None

        processed += 1

    if processed:
        db.commit()

    return processed
