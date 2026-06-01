from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.management_setup import (
    ManagementClassSubjectCreateIn,
    ManagementClassSubjectsResponse,
    ManagementClassSubjectOut,
    ManagementSchoolProfileOut,
    ManagementSchoolProfileUpdateIn,
    ManagementSectionCreateIn,
    ManagementSectionGroupOut,
    ManagementSectionOut,
    ManagementSetupCompleteOut,
    ManagementSetupStatusOut,
)
from app.db.models.user import User
from app.services import management_setup as management_setup_service

router = APIRouter(prefix="/management", tags=["management-setup"])


@router.get("/setup/status", response_model=ManagementSetupStatusOut)
def get_setup_status(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementSetupStatusOut:
    return management_setup_service.get_setup_status(
        db,
        school_id=school_id,
        current_user=current_user,
    )


@router.post("/setup/complete", response_model=ManagementSetupCompleteOut)
def complete_setup(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementSetupCompleteOut:
    return management_setup_service.complete_setup(
        db,
        school_id=school_id,
        current_user=current_user,
    )


@router.get("/school-profile", response_model=ManagementSchoolProfileOut)
def get_management_school_profile(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementSchoolProfileOut:
    return management_setup_service.get_school_profile(
        db,
        school_id=school_id,
        current_user=current_user,
    )


@router.patch("/school-profile", response_model=ManagementSchoolProfileOut)
def update_management_school_profile(
    payload: ManagementSchoolProfileUpdateIn,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementSchoolProfileOut:
    return management_setup_service.update_school_profile(
        db,
        school_id=school_id,
        payload=payload,
        current_user=current_user,
    )


@router.get("/sections", response_model=list[ManagementSectionGroupOut])
def list_management_sections(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> list[ManagementSectionGroupOut]:
    return management_setup_service.list_sections(
        db,
        school_id=school_id,
        current_user=current_user,
    )


@router.post("/sections", response_model=ManagementSectionOut, status_code=status.HTTP_201_CREATED)
def create_management_section(
    payload: ManagementSectionCreateIn,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementSectionOut:
    return management_setup_service.create_section(
        db,
        school_id=school_id,
        payload=payload,
        current_user=current_user,
    )


@router.delete("/sections/{section_id}")
def delete_management_section(
    section_id: int,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> dict[str, bool]:
    return management_setup_service.delete_section(
        db,
        school_id=school_id,
        section_id=section_id,
        current_user=current_user,
    )


@router.get("/subjects", response_model=ManagementClassSubjectsResponse)
def list_management_subjects(
    class_id: int = Query(...),
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementClassSubjectsResponse:
    return management_setup_service.list_class_subjects(
        db,
        school_id=school_id,
        class_id=class_id,
        current_user=current_user,
    )


@router.post("/subjects", response_model=ManagementClassSubjectOut, status_code=status.HTTP_201_CREATED)
def create_management_subject(
    payload: ManagementClassSubjectCreateIn,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementClassSubjectOut:
    return management_setup_service.create_class_subject(
        db,
        school_id=school_id,
        payload=payload,
        current_user=current_user,
    )


@router.delete("/subjects/{class_subject_id}")
def delete_management_subject(
    class_subject_id: int,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> dict[str, bool]:
    return management_setup_service.delete_class_subject(
        db,
        school_id=school_id,
        class_subject_id=class_subject_id,
        current_user=current_user,
    )
