from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.roles import normalize_role
from app.db.models.audit_log import AuditLog
from app.db.models.class_ import Class
from app.db.models.fee_head import FeeHead
from app.db.models.fee_payment import FeePayment, FeePaymentItem
from app.db.models.fee_receipt_counter import FeeReceiptCounter
from app.db.models.fee_structure import FeeStructure
from app.db.models.fee_structure_item import FeeStructureItem
from app.db.models.school import School
from app.db.models.school_contact import SchoolContact
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.user import User


def _parse_iso_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=422, detail={"code": "INVALID_PAYMENT_DATE"})
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _student_grade_name(class_name: str | None) -> str | None:
    if not class_name:
        return None
    token = class_name.strip()
    if not token:
        return None
    if token.isdigit():
        return f"Grade {int(token)}"
    key = re.sub(r"\s+", " ", token).strip()
    return key


def _load_fee_plan(
    db: Session,
    *,
    school_id: int,
    session: str,
    grade_name: str,
) -> tuple[FeeStructure, list[FeeStructureItem], dict[int, FeeHead], int]:
    structure = (
        db.query(FeeStructure)
        .filter(
            FeeStructure.school_id == school_id,
            FeeStructure.session == session,
            FeeStructure.grade_name == grade_name,
            FeeStructure.is_active.is_(True),
        )
        .first()
    )
    if not structure:
        raise HTTPException(
            status_code=404,
            detail={"code": "FEE_PLAN_NOT_FOUND", "session": session, "grade_name": grade_name},
        )

    items = (
        db.query(FeeStructureItem)
        .filter(FeeStructureItem.fee_structure_id == structure.id)
        .all()
    )
    head_ids = sorted({i.fee_head_id for i in items})
    heads = (
        db.query(FeeHead)
        .filter(FeeHead.school_id == school_id, FeeHead.id.in_(head_ids))
        .all()
        if head_ids
        else []
    )
    head_by_id = {h.id: h for h in heads}
    total_due = sum(int(i.amount or 0) for i in items)
    return structure, items, head_by_id, int(total_due)


def get_student_fee_due(
    db: Session,
    *,
    school_id: int,
    student_id: int,
    session: str,
) -> dict[str, Any]:
    student = db.query(Student).filter(Student.id == student_id, Student.school_id == school_id).first()
    if not student:
        raise HTTPException(status_code=404, detail={"code": "STUDENT_NOT_FOUND"})

    section = None
    class_row = None
    if student.section_id:
        section = db.query(Section).filter(Section.id == student.section_id, Section.school_id == school_id).first()
        if section:
            class_row = db.query(Class).filter(Class.id == section.class_id, Class.school_id == school_id).first()

    grade_name = _student_grade_name(class_row.name if class_row else None)
    if not grade_name:
        raise HTTPException(status_code=400, detail={"code": "STUDENT_GRADE_NOT_SET"})

    structure, items, head_by_id, total_due = _load_fee_plan(
        db,
        school_id=school_id,
        session=session,
        grade_name=grade_name,
    )

    total_paid = (
        db.execute(
            select(func.coalesce(func.sum(FeePayment.amount_paid), 0))
            .where(
                FeePayment.school_id == school_id,
                FeePayment.student_id == student_id,
                FeePayment.session == session,
            )
        )
        .scalar_one()
    )
    total_paid = int(total_paid or 0)
    balance = max(0, total_due - total_paid)
    status_label = "paid_in_full" if balance == 0 and total_due > 0 else ("partial" if total_paid > 0 else "pending")

    breakdown = []
    for it in items:
        head = head_by_id.get(it.fee_head_id)
        breakdown.append(
            {
                "fee_head_id": it.fee_head_id,
                "category_name": head.name if head else "Unknown",
                "amount": int(it.amount),
            }
        )

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "section": section.name if section else None,
            "grade_name": grade_name,
        },
        "plan": {
            "fee_structure_id": structure.id,
            "session": structure.session,
            "grade_name": structure.grade_name,
            "items": breakdown,
            "total_due": total_due,
        },
        "summary": {
            "total_paid": total_paid,
            "balance_due": balance,
            "status": status_label,
        },
    }


def _next_receipt_number(db: Session, *, school_id: int, year: int) -> str:
    counter = (
        db.query(FeeReceiptCounter)
        .filter(FeeReceiptCounter.school_id == school_id, FeeReceiptCounter.year == year)
        .with_for_update()
        .first()
    )
    if counter is None:
        seq = 1
        counter = FeeReceiptCounter(school_id=school_id, year=year, next_seq=2)
        db.add(counter)
        db.flush()
    else:
        seq = int(counter.next_seq)
        counter.next_seq = seq + 1
        db.add(counter)
        db.flush()
    return f"RCP-{year}-{seq:04d}"


def _compute_outstanding_by_head(
    *,
    plan_items: list[FeeStructureItem],
    prior_paid_items: list[FeePaymentItem],
) -> dict[int, int]:
    due_by_head: dict[int, int] = {}
    for it in plan_items:
        due_by_head[it.fee_head_id] = due_by_head.get(it.fee_head_id, 0) + int(it.amount or 0)
    paid_by_head: dict[int, int] = {}
    for it in prior_paid_items:
        paid_by_head[it.fee_head_id] = paid_by_head.get(it.fee_head_id, 0) + int(it.amount or 0)
    out: dict[int, int] = {}
    for head_id, due in due_by_head.items():
        out[head_id] = max(0, int(due) - int(paid_by_head.get(head_id, 0)))
    return out


def _auto_allocate_items(
    *,
    amount_paid: int,
    plan_items: list[FeeStructureItem],
    outstanding_by_head: dict[int, int],
) -> list[dict[str, int]]:
    remaining = int(amount_paid)
    allocated: list[dict[str, int]] = []
    for it in plan_items:
        head_id = it.fee_head_id
        outstanding = int(outstanding_by_head.get(head_id, 0))
        if outstanding <= 0:
            continue
        if remaining <= 0:
            break
        take = min(remaining, outstanding)
        allocated.append({"fee_head_id": head_id, "amount": int(take)})
        remaining -= int(take)
    if remaining > 0:
        # If remaining couldn't be allocated to plan heads, allocate to the first head as advance.
        if plan_items:
            allocated.append({"fee_head_id": plan_items[0].fee_head_id, "amount": int(remaining)})
    return allocated


def record_fee_payment(
    db: Session,
    *,
    school_id: int,
    payload: dict[str, Any],
    current_user: User,
) -> dict[str, Any]:
    student_id = int(payload["student_id"])
    session = str(payload["session"]).strip()
    amount_paid = int(payload["amount_paid"])
    payment_mode = str(payload["payment_mode"]).strip().lower()
    payment_date = _parse_iso_dt(str(payload["payment_date"]))
    note = payload.get("note")
    requested_items = payload.get("items")

    due = get_student_fee_due(db, school_id=school_id, student_id=student_id, session=session)
    balance = int(due["summary"]["balance_due"])
    total_due = int(due["plan"]["total_due"])

    if total_due <= 0:
        raise HTTPException(status_code=400, detail={"code": "FEE_PLAN_TOTAL_ZERO"})
    if amount_paid <= 0:
        raise HTTPException(status_code=422, detail={"code": "INVALID_AMOUNT"})
    if amount_paid > balance:
        raise HTTPException(status_code=422, detail={"code": "AMOUNT_EXCEEDS_BALANCE", "balance_due": balance})

    fee_structure_id = int(due["plan"]["fee_structure_id"])

    # Load plan items for allocation/validation
    structure, plan_items, head_by_id, _ = _load_fee_plan(
        db,
        school_id=school_id,
        session=session,
        grade_name=str(due["student"]["grade_name"]),
    )
    prior_payment_ids = (
        db.execute(
            select(FeePayment.id)
            .where(
                FeePayment.school_id == school_id,
                FeePayment.student_id == student_id,
                FeePayment.session == session,
            )
        )
        .scalars()
        .all()
    )
    prior_items = (
        db.query(FeePaymentItem)
        .filter(FeePaymentItem.payment_id.in_(prior_payment_ids))
        .all()
        if prior_payment_ids
        else []
    )
    outstanding_by_head = _compute_outstanding_by_head(plan_items=plan_items, prior_paid_items=prior_items)

    # Determine payment items
    items_to_store: list[dict[str, int]]
    if requested_items is None:
        items_to_store = _auto_allocate_items(
            amount_paid=amount_paid,
            plan_items=plan_items,
            outstanding_by_head=outstanding_by_head,
        )
    else:
        if not isinstance(requested_items, list) or len(requested_items) == 0:
            raise HTTPException(status_code=422, detail={"code": "INVALID_PAYMENT_ITEMS"})
        summed = sum(int(i.get("amount") or 0) for i in requested_items)
        if summed != amount_paid:
            raise HTTPException(status_code=422, detail={"code": "PAYMENT_ITEMS_SUM_MISMATCH", "sum": summed, "amount_paid": amount_paid})
        # Validate fee_head_ids belong to this school
        head_ids = [int(i["fee_head_id"]) for i in requested_items]
        valid_heads = (
            db.query(FeeHead.id)
            .filter(FeeHead.school_id == school_id, FeeHead.id.in_(head_ids), FeeHead.is_active.is_(True))
            .all()
        )
        if len(valid_heads) != len(set(head_ids)):
            raise HTTPException(status_code=422, detail={"code": "INVALID_FEE_CATEGORIES"})
        items_to_store = [{"fee_head_id": int(i["fee_head_id"]), "amount": int(i["amount"])} for i in requested_items]

    # Generate receipt number per school+year
    receipt_year = int(payment_date.astimezone(timezone.utc).year)
    receipt_number = _next_receipt_number(db, school_id=school_id, year=receipt_year)

    payment = FeePayment(
        school_id=school_id,
        student_id=student_id,
        fee_structure_id=fee_structure_id,
        session=session,
        amount_paid=amount_paid,
        payment_mode=payment_mode,
        payment_date=payment_date,
        receipt_number=receipt_number,
        note=note,
        recorded_by_user_id=current_user.id,
    )
    db.add(payment)
    db.flush()

    for row in items_to_store:
        db.add(
            FeePaymentItem(
                payment_id=payment.id,
                fee_head_id=int(row["fee_head_id"]),
                amount=int(row["amount"]),
            )
        )

    db.add(AuditLog(user_id=current_user.id, event="fee_payment_recorded", identifier=str(student_id)))

    db.commit()

    # Build receipt output
    updated_due = get_student_fee_due(db, school_id=school_id, student_id=student_id, session=session)
    items_out = []
    for row in items_to_store:
        head = head_by_id.get(int(row["fee_head_id"]))
        items_out.append(
            {
                "fee_head_id": int(row["fee_head_id"]),
                "category_name": head.name if head else "Unknown",
                "amount": int(row["amount"]),
            }
        )

    return {
        "payment": {
            "id": payment.id,
            "receipt_number": receipt_number,
            "session": session,
            "student_id": student_id,
            "amount_paid": amount_paid,
            "payment_mode": payment_mode,
            "payment_date": payment.payment_date.isoformat(),
            "note": payment.note,
            "recorded_by": current_user.full_name or current_user.email or current_user.phone,
            "items": items_out,
        },
        "summary": updated_due["summary"],
    }


def get_fee_payment_receipt(
    db: Session,
    *,
    school_id: int,
    payment_id: int,
) -> dict[str, Any]:
    payment = (
        db.query(FeePayment)
        .filter(FeePayment.id == payment_id, FeePayment.school_id == school_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail={"code": "PAYMENT_NOT_FOUND"})

    student = db.query(Student).filter(Student.id == payment.student_id, Student.school_id == school_id).first()
    section = None
    class_row = None
    if student and student.section_id:
        section = db.query(Section).filter(Section.id == student.section_id).first()
        if section:
            class_row = db.query(Class).filter(Class.id == section.class_id).first()

    school = db.query(School).filter(School.id == school_id).first()
    contact = db.query(SchoolContact).filter(SchoolContact.school_id == school_id).first()

    recorder = db.query(User).filter(User.id == payment.recorded_by_user_id).first()

    items = (
        db.query(FeePaymentItem, FeeHead)
        .join(FeeHead, FeeHead.id == FeePaymentItem.fee_head_id)
        .filter(FeePaymentItem.payment_id == payment.id)
        .all()
    )

    item_rows = []
    for it, head in items:
        item_rows.append({"category": head.name, "amount": int(it.amount)})

    return {
        "receipt": {
            "receipt_number": payment.receipt_number,
            "payment_date": payment.payment_date.isoformat(),
            "payment_mode": payment.payment_mode,
            "amount_paid": int(payment.amount_paid),
            "note": payment.note,
            "session": payment.session,
        },
        "school": {
            "name": school.name if school else None,
            "vt_school_id": school.public_id if school else None,
            "phone": contact.school_phone if contact else None,
            "email": contact.school_email if contact else None,
            "address": {
                "street": contact.street if contact else None,
                "area": contact.area if contact else None,
                "city": contact.city if contact else None,
                "district": contact.district if contact else None,
                "state": contact.state if contact else None,
                "pincode": contact.pin_code if contact else None,
            },
        },
        "student": {
            "name": student.name if student else None,
            "roll_number": student.roll_number if student else None,
            "section": section.name if section else None,
            "class": class_row.name if class_row else None,
        },
        "items": item_rows,
        "received_by": recorder.full_name if recorder else None,
    }


def list_fee_payments(
    db: Session,
    *,
    school_id: int,
    session: str | None = None,
    student_id: int | None = None,
    grade_name: str | None = None,
    payment_mode: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    q = db.query(FeePayment).filter(FeePayment.school_id == school_id)
    if session:
        q = q.filter(FeePayment.session == session)
    if student_id:
        q = q.filter(FeePayment.student_id == student_id)
    if payment_mode:
        q = q.filter(FeePayment.payment_mode == payment_mode)
    if date_from:
        q = q.filter(FeePayment.payment_date >= _parse_iso_dt(date_from))
    if date_to:
        q = q.filter(FeePayment.payment_date <= _parse_iso_dt(date_to))
    q = q.order_by(FeePayment.payment_date.desc()).limit(int(limit))
    rows = q.all()

    student_ids = sorted({p.student_id for p in rows})
    students = (
        db.query(Student).filter(Student.school_id == school_id, Student.id.in_(student_ids)).all()
        if student_ids
        else []
    )
    student_by_id = {s.id: s for s in students}

    # Derive class names for students
    section_ids = sorted({s.section_id for s in students if s.section_id})
    sections = db.query(Section).filter(Section.school_id == school_id, Section.id.in_(section_ids)).all() if section_ids else []
    section_by_id = {s.id: s for s in sections}
    class_ids = sorted({s.class_id for s in sections})
    classes = db.query(Class).filter(Class.school_id == school_id, Class.id.in_(class_ids)).all() if class_ids else []
    class_by_id = {c.id: c for c in classes}

    out_rows = []
    for p in rows:
        s = student_by_id.get(p.student_id)
        sec = section_by_id.get(s.section_id) if s and s.section_id else None
        cls = class_by_id.get(sec.class_id) if sec else None
        grade = _student_grade_name(cls.name if cls else None)
        if grade_name and grade != grade_name:
            continue
        out_rows.append(
            {
                "payment_id": p.id,
                "payment_date": p.payment_date.isoformat(),
                "student_id": p.student_id,
                "student_name": s.name if s else None,
                "grade_name": grade,
                "section": sec.name if sec else None,
                "amount_paid": int(p.amount_paid),
                "payment_mode": p.payment_mode,
                "receipt_number": p.receipt_number,
                "session": p.session,
            }
        )

    # Totals
    now = datetime.now(timezone.utc)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_total_q = db.query(func.coalesce(func.sum(FeePayment.amount_paid), 0)).filter(FeePayment.school_id == school_id)
    if session:
        base_total_q = base_total_q.filter(FeePayment.session == session)
    total_today = int(base_total_q.filter(FeePayment.payment_date >= start_today).scalar() or 0)
    total_month = int(base_total_q.filter(FeePayment.payment_date >= start_month).scalar() or 0)

    return {
        "rows": out_rows,
        "totals": {
            "collected_today": total_today,
            "collected_this_month": total_month,
        },
    }


def export_fee_payments_csv(
    db: Session,
    *,
    school_id: int,
    session: str | None = None,
    payment_mode: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    data = list_fee_payments(
        db,
        school_id=school_id,
        session=session,
        payment_mode=payment_mode,
        date_from=date_from,
        date_to=date_to,
        limit=10_000,
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Student", "Grade", "Section", "Amount", "Mode", "Receipt", "Session"])
    for r in data["rows"]:
        writer.writerow([
            r["payment_date"],
            r["student_name"] or "",
            r["grade_name"] or "",
            r["section"] or "",
            r["amount_paid"],
            r["payment_mode"],
            r["receipt_number"],
            r["session"],
        ])
    return buf.getvalue()

