from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    get_db,
    require_management_or_super_admin,
    require_management_or_principal_or_super_admin,
    require_school_module,
)
from app.api.v1.schemas.fees import (
    FeeCategoryCreateIn,
    FeeHeadCreateIn,
    FeeHeadOut,
    FeePaymentCreateIn,
    FeeStructureCreateIn,
)
from app.db.models.user import User
from app.services import fees as fees_service
from app.services import fee_payments as fee_payments_service
from fastapi.responses import Response
from fastapi import Query, Path


router = APIRouter(prefix="/fees", tags=["fees"])


@router.get("/heads", response_model=list[FeeHeadOut])
def list_fee_heads(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> list[FeeHeadOut]:
    rows = fees_service.list_fee_heads(db, school_id=school_id)
    return [
        FeeHeadOut(id=r.id, name=r.name, code=r.code, is_active=bool(r.is_active))
        for r in rows
    ]


@router.post("/heads", response_model=FeeHeadOut, status_code=201)
def create_fee_head(
    payload: FeeHeadCreateIn,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> FeeHeadOut:
    row = fees_service.create_fee_head(
        db,
        school_id=school_id,
        name=payload.name,
        code=payload.code,
    )
    return FeeHeadOut(id=row.id, name=row.name, code=row.code, is_active=bool(row.is_active))


@router.get("/categories", response_model=list[FeeHeadOut])
def list_fee_categories(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> list[FeeHeadOut]:
    rows = fees_service.list_fee_heads(db, school_id=school_id)
    return [
        FeeHeadOut(id=r.id, name=r.name, code=r.code, is_active=bool(r.is_active))
        for r in rows
    ]


@router.post("/categories", response_model=FeeHeadOut, status_code=201)
def create_fee_category(
    payload: FeeCategoryCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> FeeHeadOut:
    row = fees_service.create_fee_category(db, school_id=school_id, name=payload.name, current_user=current_user)
    return FeeHeadOut(id=row.id, name=row.name, code=row.code, is_active=bool(row.is_active))


@router.get("/structures")
def list_fee_structures(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> dict:
    return {"success": True, "data": fees_service.list_fee_structures(db, school_id=school_id)}


@router.post("/structures", status_code=201)
def create_fee_structure(
    payload: FeeStructureCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> dict:
    created = fees_service.create_fee_structure(
        db,
        school_id=school_id,
        name=payload.name,
        session=payload.session,
        grade_name=payload.grade_name,
        items=[i.model_dump() for i in payload.items],
        current_user=current_user,
    )
    return {"success": True, "data": created}


@router.get("/plans")
def list_fee_plans(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> dict:
    return {"success": True, "data": fees_service.list_fee_structures(db, school_id=school_id)}


@router.post("/plans", status_code=201)
def create_fee_plan(
    payload: FeeStructureCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> dict:
    created = fees_service.create_fee_structure(
        db,
        school_id=school_id,
        name=payload.name,
        session=payload.session,
        grade_name=payload.grade_name,
        items=[i.model_dump() for i in payload.items],
        current_user=current_user,
    )
    return {"success": True, "data": created}


@router.get("/due")
def get_fee_due(
    student_id: int = Query(..., ge=1),
    session: str = Query(..., min_length=4, max_length=16),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> dict:
    data = fee_payments_service.get_student_fee_due(db, school_id=school_id, student_id=student_id, session=session)
    return {"success": True, "data": data}


@router.post("/payments", status_code=201)
def record_payment(
    payload: FeePaymentCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> dict:
    data = fee_payments_service.record_fee_payment(
        db,
        school_id=school_id,
        payload=payload.model_dump(),
        current_user=current_user,
    )
    return {"success": True, "data": data}


@router.get("/payments")
def list_payments(
    session: str | None = Query(default=None),
    student_id: int | None = Query(default=None, ge=1),
    grade_name: str | None = Query(default=None),
    payment_mode: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> dict:
    data = fee_payments_service.list_fee_payments(
        db,
        school_id=school_id,
        session=session,
        student_id=student_id,
        grade_name=grade_name,
        payment_mode=payment_mode,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return {"success": True, "data": data}


@router.get("/payments/{payment_id}/receipt")
def get_receipt(
    payment_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> dict:
    data = fee_payments_service.get_fee_payment_receipt(db, school_id=school_id, payment_id=payment_id)
    return {"success": True, "data": data}


@router.get("/payments/export.csv")
def export_payments_csv(
    session: str | None = Query(default=None),
    payment_mode: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_management_or_principal_or_super_admin),
    school_id: int = Depends(require_school_module("fees")),
) -> Response:
    csv_text = fee_payments_service.export_fee_payments_csv(
        db,
        school_id=school_id,
        session=session,
        payment_mode=payment_mode,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(content=csv_text, media_type="text/csv")
