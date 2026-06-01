from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.fee_head import FeeHead
from app.db.models.fee_structure import FeeStructure
from app.db.models.fee_structure_item import FeeStructureItem
from app.db.models.audit_log import AuditLog
from app.db.models.user import User


def list_fee_heads(db: Session, *, school_id: int) -> list[FeeHead]:
    return (
        db.query(FeeHead)
        .filter(FeeHead.school_id == school_id, FeeHead.is_active.is_(True))
        .order_by(FeeHead.name.asc())
        .all()
    )


def create_fee_head(db: Session, *, school_id: int, name: str, code: str) -> FeeHead:
    normalized_code = code.strip().upper().replace(" ", "_")
    if not normalized_code or len(normalized_code) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_FEE_HEAD_CODE"},
        )
    row = FeeHead(
        school_id=school_id,
        name=name.strip(),
        code=normalized_code,
        is_active=True,
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(row)
    return row


def create_fee_category(db: Session, *, school_id: int, name: str, current_user: User) -> FeeHead:
    """
    Accountant-friendly alias for FeeHead:
      - Only requires a display name
      - Generates a stable code automatically
    """
    base = name.strip().upper()
    normalized = re.sub(r"[^A-Z0-9]+", "_", base).strip("_")[:20] or "FEE"
    candidate = normalized
    suffix = 1
    while True:
        exists = db.query(FeeHead.id).filter(FeeHead.school_id == school_id, FeeHead.code == candidate).first()
        if not exists:
            break
        suffix_str = str(suffix)
        trim = max(1, 20 - (len(suffix_str) + 1))
        candidate = f"{normalized[:trim]}_{suffix_str}"
        suffix += 1

    row = FeeHead(school_id=school_id, name=name.strip(), code=candidate, is_active=True)
    db.add(row)
    db.flush()
    db.add(AuditLog(user_id=current_user.id, event="fee_head_created", identifier=str(school_id)))
    db.commit()
    db.refresh(row)
    return row


def list_fee_structures(db: Session, *, school_id: int) -> list[dict]:
    structures = (
        db.query(FeeStructure)
        .filter(FeeStructure.school_id == school_id, FeeStructure.is_active.is_(True))
        .order_by(FeeStructure.session.desc(), FeeStructure.grade_name.asc())
        .all()
    )
    if not structures:
        return []

    structure_ids = [s.id for s in structures]
    items = (
        db.query(FeeStructureItem)
        .filter(FeeStructureItem.fee_structure_id.in_(structure_ids))
        .all()
    )
    items_by_structure: dict[int, list[FeeStructureItem]] = {}
    for item in items:
        items_by_structure.setdefault(item.fee_structure_id, []).append(item)

    # Load heads referenced by items
    head_ids = sorted({i.fee_head_id for i in items})
    heads = (
        db.query(FeeHead)
        .filter(FeeHead.id.in_(head_ids))
        .all()
        if head_ids
        else []
    )
    head_by_id = {h.id: h for h in heads}

    out: list[dict] = []
    for s in structures:
        its = items_by_structure.get(s.id, [])
        rows = []
        total = 0
        for it in its:
            head = head_by_id.get(it.fee_head_id)
            rows.append(
                {
                    "fee_head_id": it.fee_head_id,
                    "fee_head_code": head.code if head else None,
                    "fee_head_name": head.name if head else None,
                    "amount": int(it.amount),
                }
            )
            total += int(it.amount or 0)
        out.append(
            {
                "id": s.id,
                "name": s.name,
                "session": s.session,
                "grade_name": s.grade_name,
                "is_active": bool(s.is_active),
                "total_amount": total,
                "items": rows,
            }
        )
    return out


def create_fee_structure(
    db: Session,
    *,
    school_id: int,
    name: str | None,
    session: str,
    grade_name: str,
    items: list[dict],
    current_user: User | None = None,
) -> dict:
    # Validate heads exist for this school
    head_ids = [int(i["fee_head_id"]) for i in items]
    heads = (
        db.query(FeeHead)
        .filter(FeeHead.school_id == school_id, FeeHead.id.in_(head_ids), FeeHead.is_active.is_(True))
        .all()
    )
    if len(heads) != len(set(head_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_FEE_HEADS"},
        )

    normalized_session = session.strip()
    normalized_grade_name = grade_name.strip()
    structure = (
        db.query(FeeStructure)
        .filter(
            FeeStructure.school_id == school_id,
            FeeStructure.session == normalized_session,
            FeeStructure.grade_name == normalized_grade_name,
        )
        .first()
    )
    was_existing = structure is not None
    if structure is None:
        structure = FeeStructure(
            school_id=school_id,
            name=name.strip() if name else None,
            session=normalized_session,
            grade_name=normalized_grade_name,
            is_active=True,
        )
        db.add(structure)
        db.flush()
    else:
        structure.name = name.strip() if name else None
        structure.is_active = True
        db.query(FeeStructureItem).filter(
            FeeStructureItem.fee_structure_id == structure.id
        ).delete(synchronize_session=False)

    for row in items:
        db.add(
            FeeStructureItem(
                fee_structure_id=structure.id,
                fee_head_id=int(row["fee_head_id"]),
                amount=int(row["amount"]),
            )
        )

    if current_user is not None:
        db.add(
            AuditLog(
                user_id=current_user.id,
                event="fee_structure_updated" if was_existing else "fee_structure_created",
                identifier=str(school_id),
            )
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "id": structure.id,
        "name": structure.name,
        "session": structure.session,
        "grade_name": structure.grade_name,
        "is_active": True,
        "updated_existing": was_existing,
    }
