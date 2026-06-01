import json
import ssl
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.v1.controllers import schools as schools_controller
from app.api.v1.deps import get_db, get_current_user, require_super_admin
from app.core.config import settings
from app.api.v1.schemas.schools import (
    PaginatedResponse,
    SchoolCreate,
    SchoolDashboardOut,
    SchoolOut,
    SchoolStaffListItem,
    SchoolStudentListItem,
    SchoolTeacherListItem,
)
from app.db.models.school import School
from app.db.models.user import User

router = APIRouter(prefix="/schools", tags=["schools"])

try:
    import certifi  # type: ignore
except Exception:  # pragma: no cover
    certifi = None


def _india_post_ssl_context() -> ssl.SSLContext:
    """
    Build an SSL context that works in minimal container / conda environments.
    Prefer certifi's CA bundle when available.
    """
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


@router.get("/pincode/{pincode}")
def lookup_pincode(
    pincode: str = Path(pattern=r"^\d{6}$"),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Look up city/district/state for an Indian pincode via India Post API."""
    url = f"https://api.postalpincode.in/pincode/{pincode}"
    try:
        req = Request(
            url=url,
            headers={"User-Agent": "vidyatrack-backend/1.0"},
            method="GET",
        )
        try:
            with urlopen(req, timeout=8, context=_india_post_ssl_context()) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except URLError as exc:
            # In some local dev environments, Python cannot validate system certs.
            # Retry without verification only in debug mode to keep onboarding usable.
            reason = getattr(exc, "reason", None)
            if settings.debug and isinstance(reason, ssl.SSLCertVerificationError):
                with urlopen(req, timeout=8, context=ssl._create_unverified_context()) as resp:  # noqa: S501
                    data = json.loads(resp.read().decode("utf-8"))
            else:
                raise
    except HTTPError as exc:
        detail: dict = {"code": "PINCODE_API_UNAVAILABLE", "upstream_status": exc.code}
        if settings.debug:
            detail["reason"] = "HTTPError"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
    except URLError as exc:
        detail = {"code": "PINCODE_API_UNAVAILABLE"}
        if settings.debug:
            detail["reason"] = f"URLError: {getattr(exc, 'reason', None) or 'unknown'}"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
    except Exception as exc:
        detail = {"code": "PINCODE_API_UNAVAILABLE"}
        if settings.debug:
            detail["reason"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"code": "PINCODE_NOT_FOUND"})

    entry = data[0]
    if entry.get("Status") != "Success":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"code": "PINCODE_NOT_FOUND"})

    post_offices = entry.get("PostOffice") or []
    if not post_offices:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"code": "PINCODE_NOT_FOUND"})

    po = post_offices[0]
    return {
        "pincode": pincode,
        "city": po.get("Division") or po.get("District") or "",
        "district": po.get("District") or "",
        "state": po.get("State") or "",
        "country": "India",
        # India Post API doesn't provide coordinates; keep keys for UI parity.
        "lat": None,
        "lng": None,
    }


@router.get("", response_model=PaginatedResponse[SchoolOut])
def list_schools(
    db: Session = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
) -> PaginatedResponse[SchoolOut]:
    return schools_controller.list_schools(db=db, search=search, page=page, limit=limit)


@router.get("/{school_id}/dashboard", response_model=SchoolDashboardOut)
def get_school_dashboard(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> SchoolDashboardOut:
    return schools_controller.get_school_dashboard(school_id=school_id, db=db)


@router.get("/{school_id}/teachers", response_model=PaginatedResponse[SchoolTeacherListItem])
def get_school_teachers(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
) -> PaginatedResponse[SchoolTeacherListItem]:
    return schools_controller.get_school_teachers(school_id=school_id, db=db, page=page, limit=limit)


@router.get("/{school_id}/students", response_model=PaginatedResponse[SchoolStudentListItem])
def get_school_students(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
) -> PaginatedResponse[SchoolStudentListItem]:
    return schools_controller.get_school_students(school_id=school_id, db=db, page=page, limit=limit)


@router.get("/{school_id}/staff", response_model=PaginatedResponse[SchoolStaffListItem])
def get_school_staff(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
) -> PaginatedResponse[SchoolStaffListItem]:
    return schools_controller.get_school_staff(school_id=school_id, db=db, page=page, limit=limit)


@router.post("", response_model=SchoolOut, status_code=201)
def create_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> School:
    return schools_controller.create_school(
        payload=payload,
        db=db,
        current_user=current_user,
        idempotency_key=idempotency_key,
    )
