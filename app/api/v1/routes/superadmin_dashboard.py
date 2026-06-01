from __future__ import annotations


from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_super_admin
from app.core.phone import normalize_phone
from app.db.models.user import User
from app.services.superadmin_dashboard import get_platform_dashboard
from app.services.superadmin_schools import get_superadmin_schools

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


@router.get("/dashboard")
def superadmin_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> dict:
    return get_platform_dashboard(db)


@router.get("/check-phone")
def check_phone_availability(
    phone: str = Query(..., min_length=10),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> dict:
    """Check if a phone number is already registered as a user."""
    try:
        normalized = normalize_phone(phone)
    except ValueError:
        return {"available": False, "reason": "INVALID_PHONE"}
    exists = db.query(User).filter(User.phone == normalized).first() is not None
    return {"available": not exists}


@router.get("/schools")
def superadmin_schools(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
    search: str | None = Query(None),
    status: str = Query("all"),
    setup: str = Query("all"),
    show_test: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> dict:
    return get_superadmin_schools(
        db,
        search=search or None,
        status_filter=status,
        setup_filter=setup,
        show_test=show_test,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )
