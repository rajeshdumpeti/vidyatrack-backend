#!/usr/bin/env python3
"""
backfill_staff_names.py
-----------------------
Backfills a `display_name` column on the `users` table.

For every user whose email looks like an email address (contains '@'),
derives a human-readable display name from the local part:
  john.doe@gmail.com  -> "John Doe"
  alice.smith@school.in -> "Alice Smith"

Safe to run multiple times (idempotent).

Usage:
    cd vidyatrack-backend
    python scripts/backfill_staff_names.py
"""
from __future__ import annotations

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import SessionLocal


def derive_display_name(email: str) -> str:
    """
    Derive a human-readable name from the local part of an email.
    'john.doe@gmail.com' -> 'John Doe'
    """
    local = email.split("@")[0]
    # Replace dots and underscores with spaces, then title-case
    name = local.replace(".", " ").replace("_", " ").title()
    return name


def ensure_display_name_column(db) -> bool:
    """Add display_name column to users table if it doesn't exist. Returns True if added."""
    result = db.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='display_name'"
        )
    )
    if result.fetchone():
        return False  # already exists
    db.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(255) NULL"))
    db.commit()
    print("Added display_name column to users table.")
    return True


def backfill(db) -> int:
    """
    Update display_name for users where:
      - display_name IS NULL, OR
      - display_name contains '@' (was set from raw email)
    Returns count of updated rows.
    """
    rows = db.execute(
        text(
            "SELECT id, email FROM users "
            "WHERE email IS NOT NULL AND (display_name IS NULL OR display_name LIKE '%@%')"
        )
    ).fetchall()

    if not rows:
        return 0

    updated = 0
    for row in rows:
        user_id, email = row.id, row.email
        if not email or "@" not in email:
            continue
        display_name = derive_display_name(email)
        db.execute(
            text("UPDATE users SET display_name = :dn WHERE id = :uid"),
            {"dn": display_name, "uid": user_id},
        )
        updated += 1

    db.commit()
    return updated


def main() -> None:
    db = SessionLocal()
    try:
        ensure_display_name_column(db)
        count = backfill(db)
        print(f"Updated {count} staff records.")
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
