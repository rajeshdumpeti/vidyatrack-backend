from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.v1.schemas.schools import PaginatedResponse
from app.api.v1.schemas.students import (
    StudentCreate,
    StudentImportCommitIn,
    StudentImportCommitOut,
    StudentImportPreviewOut,
    StudentOut,
    StudentProfileOut,
    StudentReportCardOut,
)
from app.db.models.student import Student
from app.db.models.user import User
from app.services import students as students_service


def list_students(*, db: Session, school_id: int, section_id: int | None) -> list[StudentOut]:
    return students_service.list_students(db=db, school_id=school_id, section_id=section_id)


def list_students_paginated(
    *,
    db: Session,
    school_id: int,
    section_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 25,
) -> PaginatedResponse[StudentOut]:
    return students_service.list_students_paginated(
        db=db,
        school_id=school_id,
        section_id=section_id,
        search=search,
        page=page,
        limit=limit,
    )


def create_student(*, db: Session, school_id: int, payload: StudentCreate) -> Student:
    return students_service.create_student(db=db, school_id=school_id, payload=payload)


async def preview_students_import(
    *,
    file: UploadFile,
    db: Session,
    school_id: int,
    current_user: User,
) -> StudentImportPreviewOut:
    return await students_service.preview_students_import(
        file=file,
        db=db,
        school_id=school_id,
        current_user=current_user,
    )


def commit_students_import(
    *,
    payload: StudentImportCommitIn,
    db: Session,
    school_id: int,
    current_user: User,
) -> StudentImportCommitOut:
    return students_service.commit_students_import(
        payload=payload,
        db=db,
        school_id=school_id,
        current_user=current_user,
    )


def get_student_profile(*, student_id: str, db: Session, school_id: int) -> StudentProfileOut:
    return students_service.get_student_profile(
        student_id=student_id,
        db=db,
        school_id=school_id,
    )


def get_student_report_card(
    *,
    student_id: str,
    db: Session,
    school_id: int,
) -> StudentReportCardOut:
    return students_service.get_student_report_card(
        student_id=student_id,
        db=db,
        school_id=school_id,
    )
