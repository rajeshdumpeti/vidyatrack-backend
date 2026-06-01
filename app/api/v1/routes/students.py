from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.api.v1.controllers import students as students_controller
from app.api.v1.deps import get_db, get_current_user, require_management, get_valid_school_id
from app.api.v1.schemas.schools import PaginatedResponse
from app.api.v1.schemas.students import (
    StudentCreate,
    StudentImportCommitIn,
    StudentImportCommitOut,
    StudentImportPreviewOut,
    StudentOut,
    StudentProfileOut,
    StudentReportCardOut,
    StudentUpdate,
)
from app.db.models.student import Student
from app.db.models.user import User

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=PaginatedResponse[StudentOut])
def list_students(
    section_id: int | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[StudentOut]:
    return students_controller.list_students_paginated(
        db=db,
        school_id=school_id,
        section_id=section_id,
        search=search,
        page=page,
        limit=limit,
    )


@router.post("", response_model=StudentOut, status_code=201)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
) -> Student:
    return students_controller.create_student(
        db=db,
        school_id=school_id,
        payload=payload,
    )


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: str,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
) -> Student:
    return students_controller.update_student(
        db=db,
        school_id=school_id,
        student_id=student_id,
        payload=payload,
    )


@router.post("/import/preview", response_model=StudentImportPreviewOut)
async def preview_students_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
) -> StudentImportPreviewOut:
    return await students_controller.preview_students_import(
        file=file,
        db=db,
        school_id=school_id,
        current_user=current_user,
    )


@router.post("/import/commit", response_model=StudentImportCommitOut)
def commit_students_import(
    payload: StudentImportCommitIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
) -> StudentImportCommitOut:
    return students_controller.commit_students_import(
        payload=payload,
        db=db,
        school_id=school_id,
        current_user=current_user,
    )


@router.get("/{student_id}", response_model=StudentProfileOut)
def get_student_profile(
    student_id: str,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
) -> StudentProfileOut:
    return students_controller.get_student_profile(
        student_id=student_id,
        db=db,
        school_id=school_id,
    )


@router.get("/{student_id}/report-card", response_model=StudentReportCardOut)
def get_student_report_card(
    student_id: str,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
) -> StudentReportCardOut:
    return students_controller.get_student_report_card(
        student_id=student_id,
        db=db,
        school_id=school_id,
    )
