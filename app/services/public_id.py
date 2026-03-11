from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.public_id_counter import PublicIdCounter
from app.db.models.school import School


ENTITY_CODES: dict[str, str] = {
    "school": "SCH",
    "class": "CLS",
    "section": "SEC",
    "subject": "SUB",
    "student": "STU",
    "teacher": "TCH",
    "principal": "PRN",
    "management_admin": "MGT",
}

SEQUENCE_WIDTH = 6
GLOBAL_COUNTER_YEAR = 0
STUDENT_ENTITY = "student"


@dataclass(frozen=True)
class PublicIdConfig:
    entity: str
    display_year: int
    counter_year: int


def _counter_year(entity: str, display_year: int) -> int:
    if entity == STUDENT_ENTITY:
        return display_year
    return GLOBAL_COUNTER_YEAR


def build_public_id(
    tenant_code: str,
    entity: str,
    *,
    display_year: int,
    seq: int,
) -> str:
    code = ENTITY_CODES[entity]
    return f"{tenant_code}-{code}-{display_year}-{seq:0{SEQUENCE_WIDTH}d}"


def normalize_tenant_code(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", value.strip().upper())
    return cleaned[:6] if cleaned else "SCH"


def derive_tenant_code(name: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", name.upper())
    if not tokens:
        return "SCH"
    if len(tokens) == 1:
        base = tokens[0][:6]
    else:
        base = "".join(token[0] for token in tokens)[:6]
    if len(base) < 3:
        base = (tokens[0][:6]).ljust(3, "X")
    return base


def ensure_unique_tenant_code(
    db: Session,
    base: str,
    *,
    exclude_school_id: int | None = None,
) -> str:
    base = normalize_tenant_code(base)
    candidate = base
    suffix = 1
    while True:
        query = db.query(School).filter(School.code == candidate)
        if exclude_school_id is not None:
            query = query.filter(School.id != exclude_school_id)
        if query.first() is None:
            break
        suffix_str = str(suffix)
        trim = max(0, 6 - len(suffix_str))
        candidate = f"{base[:trim]}{suffix_str}"
        suffix += 1
    return candidate


def get_tenant_code_for_school(db: Session, school_id: int) -> str:
    name = db.query(School.name).filter(School.id == school_id).scalar()
    derived = derive_tenant_code(name or "SCH")
    unique = ensure_unique_tenant_code(db, derived, exclude_school_id=school_id)
    current_code = db.query(School.code).filter(School.id == school_id).scalar()
    if current_code != unique:
        db.query(School).filter(School.id == school_id).update({"code": unique})
        db.flush()
    return unique


def next_public_id(
    db: Session,
    *,
    tenant_code: str,
    entity: str,
    display_year: int | None = None,
) -> str:
    if entity not in ENTITY_CODES:
        raise ValueError(f"Unsupported public_id entity: {entity}")
    display_year = display_year or datetime.now(timezone.utc).year
    counter_year = _counter_year(entity, display_year)

    counter = (
        db.query(PublicIdCounter)
        .filter(
            PublicIdCounter.tenant_code == tenant_code,
            PublicIdCounter.entity == entity,
            PublicIdCounter.year == counter_year,
        )
        .with_for_update()
        .first()
    )

    if counter is None:
        seq = 1
        counter = PublicIdCounter(
            tenant_code=tenant_code,
            entity=entity,
            year=counter_year,
            next_seq=2,
        )
        db.add(counter)
        db.flush()
    else:
        seq = counter.next_seq
        counter.next_seq += 1
        db.flush()

    return build_public_id(
        tenant_code,
        entity,
        display_year=display_year,
        seq=seq,
    )
