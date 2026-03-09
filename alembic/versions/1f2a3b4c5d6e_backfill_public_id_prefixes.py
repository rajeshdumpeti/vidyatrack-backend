"""Backfill public_id prefixes to school initials.

Revision ID: 1f2a3b4c5d6e
Revises: 9d2f4a6c8e10
Create Date: 2026-03-06 09:30:00.000000
"""

from __future__ import annotations

import re
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1f2a3b4c5d6e"
down_revision = "9d2f4a6c8e10"
branch_labels = None
depends_on = None


def _derive_tenant_code(name: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", (name or "").upper())
    if not tokens:
        return "SCH"
    if len(tokens) == 1:
        base = tokens[0][:6]
    else:
        base = "".join(token[0] for token in tokens)[:6]
    if len(base) < 3:
        base = (tokens[0][:6]).ljust(3, "X")
    return base


def _unique_code(base: str, used: set[str]) -> str:
    candidate = base
    suffix = 1
    while candidate in used:
        suffix_str = str(suffix)
        trim = max(0, 6 - len(suffix_str))
        candidate = f"{base[:trim]}{suffix_str}"
        suffix += 1
    used.add(candidate)
    return candidate


def upgrade() -> None:
    bind = op.get_bind()
    schools = bind.execute(
        sa.text("SELECT id, name, code, public_id FROM schools ORDER BY id")
    ).mappings().all()

    used_codes: set[str] = set()
    tables_with_school_id = [
        "classes",
        "sections",
        "subjects",
        "students",
        "teachers",
        "principals",
        "management_admins",
    ]

    for row in schools:
        school_id = row["id"]
        old_code = (row["code"] or "").strip()
        new_code = _unique_code(_derive_tenant_code(row["name"] or ""), used_codes)

        if not old_code or old_code == new_code:
            continue

        pattern = f"^{old_code}-"
        replacement = f"{new_code}-"

        bind.execute(
            sa.text(
                "UPDATE schools "
                "SET code = :new_code, "
                "public_id = regexp_replace(public_id, :pattern, :replacement) "
                "WHERE id = :school_id"
            ),
            {
                "new_code": new_code,
                "pattern": pattern,
                "replacement": replacement,
                "school_id": school_id,
            },
        )

        bind.execute(
            sa.text(
                "UPDATE public_id_counters "
                "SET tenant_code = :new_code "
                "WHERE tenant_code = :old_code"
            ),
            {"new_code": new_code, "old_code": old_code},
        )

        for table in tables_with_school_id:
            bind.execute(
                sa.text(
                    f"UPDATE {table} "
                    "SET public_id = regexp_replace(public_id, :pattern, :replacement) "
                    "WHERE school_id = :school_id AND public_id LIKE :like_pattern"
                ),
                {
                    "pattern": pattern,
                    "replacement": replacement,
                    "school_id": school_id,
                    "like_pattern": f"{old_code}-%",
                },
            )


def downgrade() -> None:
    # Irreversible without a stored mapping of old prefixes.
    pass
