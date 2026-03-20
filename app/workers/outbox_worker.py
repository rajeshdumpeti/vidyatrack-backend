
from __future__ import annotations

from datetime import datetime, timezone, timedelta

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
    now = datetime.now(timezone.utc)
    rows = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.status.in_(["PENDING", "FAILED"]),
            NotificationOutbox.next_attempt_at <= now,
        )
        .order_by(NotificationOutbox.id.asc())
        .limit(limit)
        .all())

    processed = 0
    MAX_ATTEMPTS = 5
    BACKOFF_MINUTES = [1, 5, 15, 60, 240]  # simple exponential-ish backoff

    for row in rows:
        try:
            # Simulated send (still stubbed)
            print(
                f"[OUTBOX][SEND] id={row.id} event={row.event_type} "
                f"to={row.recipient_phone} payload={row.payload}"
            )

            # raise Exception("test failure")

            # Success path
            row.status = "SENT"
            row.sent_at = now
            row.last_error = None

            processed += 1

        except Exception as exc:
            # Failure path
            row.attempts += 1
            row.status = "FAILED"
            row.last_error = str(exc)

            if row.attempts >= MAX_ATTEMPTS:
                # Stop retrying
                row.next_attempt_at = now + timedelta(days=365)
            else:
                delay = BACKOFF_MINUTES[min(
                    row.attempts - 1, len(BACKOFF_MINUTES) - 1)]
                row.next_attempt_at = now + timedelta(minutes=delay)

    if processed:
        db.commit()

    return processed
