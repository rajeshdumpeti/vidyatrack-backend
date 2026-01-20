from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.db.models.principal import Principal
from app.db.models.user import User

router = APIRouter(prefix="/management/principal",
                   tags=["management-principal"])


class ManagementPrincipalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=10, max_length=20)
    email: str | None = Field(default=None, min_length=5, max_length=255)

    @model_validator(mode="after")
    def normalize(self) -> "ManagementPrincipalIn":
        self.phone = self.phone.strip()
        if self.email is not None:
            self.email = self.email.strip()
            if self.email == "":
                self.email = None
        self.name = self.name.strip()
        return self


class ManagementPrincipalOut(BaseModel):
    principal_id: int
    user_id: int
    name: str
    phone: str
    email: str | None = None


@router.get("", response_model=ManagementPrincipalOut)
def get_management_principal(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_management),
):
    school_id = current_user["school_id"]

    principal = db.query(Principal).filter(
        Principal.school_id == school_id).first()
    if not principal:
        raise HTTPException(status_code=404, detail="principal_not_found")

    user = (
        db.query(User)
        .filter(User.school_id == school_id, User.id == principal.user_id)
        .first()
    )
    # If this happens, DB is inconsistent. Treat as not found for safety.
    if not user:
        raise HTTPException(status_code=404, detail="principal_not_found")

    return ManagementPrincipalOut(
        principal_id=principal.id,
        user_id=user.id,
        name=principal.name,
        phone=getattr(user, "phone", None),
        email=getattr(user, "email", None),
    )


@router.post("", response_model=ManagementPrincipalOut, status_code=201)
def upsert_management_principal(
    payload: ManagementPrincipalIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_management),
):
    school_id = current_user["school_id"]

    # 1) Find existing user by phone (tenant-scoped)
    existing_user = (
        db.query(User)
        .filter(User.school_id == school_id, User.phone == payload.phone)
        .first()
    )

    # 2) Find existing principal row (one per school)
    existing_principal = db.query(Principal).filter(
        Principal.school_id == school_id).first()

    # Helper: safely deactivate previous principal user if column exists
    def _deactivate_user_if_supported(user_obj: User) -> None:
        if hasattr(user_obj, "is_active"):
            setattr(user_obj, "is_active", False)

    # CASE A: user exists
    if existing_user:
        # Ensure role becomes PRINCIPAL (force)
        if hasattr(existing_user, "role"):
            setattr(existing_user, "role", "PRINCIPAL")
        if hasattr(existing_user, "is_active"):
            setattr(existing_user, "is_active", True)
        if payload.email is not None and hasattr(existing_user, "email"):
            setattr(existing_user, "email", payload.email)

        # A1) If principal exists and already points to this user -> idempotent 200
        if existing_principal and existing_principal.user_id == existing_user.id:
            response.status_code = status.HTTP_200_OK
            # Keep name up to date if they resend (pilot-safe)
            existing_principal.name = payload.name
            db.commit()
            db.refresh(existing_principal)
            return ManagementPrincipalOut(
                principal_id=existing_principal.id,
                user_id=existing_user.id,
                name=existing_principal.name,
                phone=getattr(existing_user, "phone", None),
                email=getattr(existing_user, "email", None),
            )

        # A2) Replacement or first principal row
        if existing_principal:
            # deactivate old principal user (if supported)
            old_user = (
                db.query(User)
                .filter(User.school_id == school_id, User.id == existing_principal.user_id)
                .first()
            )
            if old_user and old_user.id != existing_user.id:
                _deactivate_user_if_supported(old_user)

            existing_principal.user_id = existing_user.id
            existing_principal.name = payload.name
            db.commit()
            db.refresh(existing_principal)
            return ManagementPrincipalOut(
                principal_id=existing_principal.id,
                user_id=existing_user.id,
                name=existing_principal.name,
                phone=getattr(existing_user, "phone", None),
                email=getattr(existing_user, "email", None),
            )

        # No principal row yet -> create it (201)
        principal = Principal(school_id=school_id,
                              user_id=existing_user.id, name=payload.name)
        db.add(principal)
        db.commit()
        db.refresh(principal)
        return ManagementPrincipalOut(
            principal_id=principal.id,
            user_id=existing_user.id,
            name=principal.name,
            phone=getattr(existing_user, "phone", None),
            email=getattr(existing_user, "email", None),
        )

    # CASE B: user does NOT exist -> create user + principal (replace if exists)
    user_kwargs = {
        "school_id": school_id,
        "phone": payload.phone,
        "role": "PRINCIPAL",
    }
    if hasattr(User, "is_active"):
        user_kwargs["is_active"] = True
    if payload.email is not None and hasattr(User, "email"):
        user_kwargs["email"] = payload.email

    user = User(**user_kwargs)
    db.add(user)
    db.flush()  # user.id now available

    if existing_principal:
        # deactivate old principal user (if supported)
        old_user = (
            db.query(User)
            .filter(User.school_id == school_id, User.id == existing_principal.user_id)
            .first()
        )
        if old_user:
            _deactivate_user_if_supported(old_user)

        existing_principal.user_id = user.id
        existing_principal.name = payload.name
        db.commit()
        db.refresh(existing_principal)
        return ManagementPrincipalOut(
            principal_id=existing_principal.id,
            user_id=user.id,
            name=existing_principal.name,
            phone=getattr(user, "phone", None),
            email=getattr(user, "email", None),
        )

    principal = Principal(school_id=school_id,
                          user_id=user.id, name=payload.name)
    db.add(principal)
    db.commit()
    db.refresh(principal)

    return ManagementPrincipalOut(
        principal_id=principal.id,
        user_id=user.id,
        name=principal.name,
        phone=getattr(user, "phone", None),
        email=getattr(user, "email", None),
    )
