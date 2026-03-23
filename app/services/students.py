from __future__ import annotations

import csv
import io
import math
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.schemas.schools import PaginatedResponse
from app.api.v1.schemas.students import (
    StudentCreate,
    StudentAttendanceSummary,
    StudentGuardianOut,
    StudentImportCommitIn,
    StudentImportCommitOut,
    StudentImportPreviewOut,
    StudentImportRowOut,
    StudentOut,
    StudentPersonalDetails,
    StudentProfileOut,
    StudentRecentResult,
    StudentReportCardOut,
    StudentReportCardRow,
)
from app.db.models.class_ import Class
from app.core.phone import normalize_phone
from app.db.models.student import Student
from app.db.models.user import User
from app.db.repositories import students as students_repository
from app.services.public_id import get_tenant_code_for_school, next_public_id

MAX_IMPORT_ROWS = 5000
IMPORT_TTL_MINUTES = 30


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_key(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_class_key(value: str | None) -> str:
    if not value:
        return ""
    text = _normalize_key(value)
    text = text.replace("-", " ")
    tokens = [t for t in text.split() if t not in {"grade", "class", "std", "standard"}]
    if not tokens:
        return ""
    joined = " ".join(tokens)
    digits = "".join(ch for ch in joined if ch.isdigit())
    if digits:
        return digits
    ordinal_map = {
        "first": "1",
        "second": "2",
        "third": "3",
        "fourth": "4",
        "fifth": "5",
        "sixth": "6",
        "seventh": "7",
        "eighth": "8",
        "ninth": "9",
        "tenth": "10",
        "eleventh": "11",
        "twelfth": "12",
    }
    if joined in ordinal_map:
        return ordinal_map[joined]
    return joined.replace(" ", "")


def _parse_iso_date(value: str | None, field: str, errors: list[str]) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field}_must_be_yyyy_mm_dd")
        return None


def _validate_gender(value: str | None, errors: list[str]) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized not in {"male", "female", "other"}:
        errors.append("gender_must_be_male_female_or_other")
        return None
    return normalized


def _resolve_full_name(
    first_name: str | None,
    last_name: str | None,
    name: str | None,
) -> str | None:
    if first_name or last_name:
        return f"{first_name or ''} {last_name or ''}".strip() or None
    return name


def _row_duplicate_key(
    section_id: int,
    roll_number: str | None,
    full_name: str | None,
    parent_phone: str | None,
    dob: date | None,
) -> tuple:
    if roll_number:
        return ("roll", section_id, roll_number.strip().lower())
    return (
        "identity",
        section_id,
        _normalize_key(full_name),
        normalize_phone(parent_phone or ""),
        dob.isoformat() if dob else "",
    )


def _grade_from_percentage(percentage: float) -> str:
    if percentage >= 90:
        return "A+"
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B+"
    if percentage >= 60:
        return "B"
    if percentage >= 50:
        return "C"
    if percentage >= 35:
        return "D"
    return "F"


def _build_student_out(
    student: Student,
    section_name: str | None,
    class_: Class | None,
) -> StudentOut:
    return StudentOut(
        id=student.id,
        public_id=student.public_id,
        school_id=student.school_id,
        student_code=student.public_id,
        name=student.name,
        first_name=student.first_name,
        last_name=student.last_name,
        date_of_birth=student.date_of_birth,
        gender=student.gender,
        section_id=student.section_id,
        section_name=section_name,
        class_id=class_.id if class_ else None,
        class_name=class_.name if class_ else None,
        roll_number=student.roll_number,
        admission_date=student.admission_date,
        parent_phone=student.parent_phone,
        parent_name=student.parent_name,
        status="active",
    )


def list_students(*, db: Session, school_id: int, section_id: int | None) -> list[StudentOut]:
    rows = students_repository.list_students_with_sections(
        db,
        school_id=school_id,
        section_id=section_id,
    )
    return [
        _build_student_out(student, section.name if section else None, class_)
        for student, section, class_ in rows
    ]


def list_students_paginated(
    *,
    db: Session,
    school_id: int,
    section_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 25,
) -> PaginatedResponse[StudentOut]:
    rows, total = students_repository.list_students_paginated(
        db,
        school_id=school_id,
        section_id=section_id,
        search=search,
        page=page,
        limit=limit,
    )
    items = [
        _build_student_out(student, section.name if section else None, class_)
        for student, section, class_ in rows
    ]
    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if limit else 1,
    )


def create_student(*, db: Session, school_id: int, payload: StudentCreate) -> Student:
    if payload.section_id is not None:
        section = students_repository.get_section_for_school(
            db,
            school_id=school_id,
            section_id=payload.section_id,
        )
        if not section:
            raise HTTPException(status_code=400, detail="invalid_section_id")

    full_name = (
        payload.name
        if payload.name and payload.name.strip()
        else f"{payload.first_name} {payload.last_name}".strip()
    )
    admission_year = payload.admission_date.year if payload.admission_date else None
    tenant_code = get_tenant_code_for_school(db, school_id)

    student = Student(
        school_id=school_id,
        name=full_name,
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        section_id=payload.section_id,
        roll_number=payload.roll_number,
        admission_date=payload.admission_date,
        parent_phone=payload.parent_phone,
        parent_name=payload.parent_name,
        public_id=next_public_id(
            db,
            tenant_code=tenant_code,
            entity="student",
            display_year=admission_year,
        ),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


async def preview_students_import(
    *,
    file: UploadFile,
    db: Session,
    school_id: int,
    current_user: User,
) -> StudentImportPreviewOut:
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="only_csv_supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty_file")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="invalid_file_encoding")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="missing_headers")

    sections = students_repository.list_sections_with_classes(db, school_id=school_id)
    section_map: dict[tuple[str, str], int] = {
        (_normalize_class_key(class_.name), _normalize_key(section.name)): section.id
        for section, class_ in sections
    }

    rows_out: list[StudentImportRowOut] = []
    valid_payload_rows: list[dict[str, Any]] = []
    file_seen_keys: set[tuple] = set()

    alias_map = {
        "first_name": ["first_name", "firstname"],
        "last_name": ["last_name", "lastname"],
        "name": ["name", "full_name", "student_name"],
        "parent_phone": ["parent_phone", "phone", "mobile", "mobile_number"],
        "parent_name": ["parent_name", "guardian_name", "parent"],
        "date_of_birth": ["date_of_birth", "dob"],
        "gender": ["gender"],
        "class_name": ["class_name", "class"],
        "section_name": ["section_name", "section"],
        "roll_number": ["roll_number", "roll_no", "roll"],
        "admission_date": ["admission_date", "date_of_admission"],
    }

    def pick(raw_row: dict[str, Any], key: str) -> str | None:
        aliases = alias_map[key]
        for alias in aliases:
            if alias in raw_row:
                return _clean_text(raw_row.get(alias))
        return None

    parsed_rows = list(reader)
    if len(parsed_rows) > MAX_IMPORT_ROWS:
        raise HTTPException(status_code=400, detail=f"max_{MAX_IMPORT_ROWS}_rows_allowed")

    for idx, raw in enumerate(parsed_rows, start=2):
        normalized_row = {
            _normalize_key(key).replace(" ", "_"): value
            for key, value in (raw or {}).items()
            if key is not None
        }
        errors: list[str] = []

        first_name = pick(normalized_row, "first_name")
        last_name = pick(normalized_row, "last_name")
        name = pick(normalized_row, "name")
        parent_phone_raw = pick(normalized_row, "parent_phone")
        parent_phone = normalize_phone(parent_phone_raw or "")
        parent_name = pick(normalized_row, "parent_name")
        class_name = pick(normalized_row, "class_name")
        section_name = pick(normalized_row, "section_name")
        roll_number = pick(normalized_row, "roll_number")
        dob = _parse_iso_date(pick(normalized_row, "date_of_birth"), "date_of_birth", errors)
        admission_date = _parse_iso_date(
            pick(normalized_row, "admission_date"),
            "admission_date",
            errors,
        )
        gender = _validate_gender(pick(normalized_row, "gender"), errors)

        full_name = _resolve_full_name(first_name, last_name, name)
        if not full_name:
            errors.append("name_or_first_last_required")
        if not parent_phone or len(parent_phone) < 10:
            errors.append("parent_phone_required_or_invalid")
        if not class_name:
            errors.append("class_name_required")
        if not section_name:
            errors.append("section_name_required")

        section_id = None
        if class_name and section_name:
            section_id = section_map.get(
                (_normalize_class_key(class_name), _normalize_key(section_name))
            )
            if not section_id:
                errors.append("class_section_not_found")

        status: Literal["valid", "invalid", "duplicate"] = "valid"
        if errors:
            status = "invalid"
        else:
            dup_key = _row_duplicate_key(
                section_id=section_id,  # type: ignore[arg-type]
                roll_number=roll_number,
                full_name=full_name,
                parent_phone=parent_phone,
                dob=dob,
            )
            if dup_key in file_seen_keys:
                status = "duplicate"
                errors.append("duplicate_in_file")
            else:
                file_seen_keys.add(dup_key)
                exists = None
                if roll_number:
                    exists = students_repository.find_student_duplicate_by_roll_number(
                        db,
                        school_id=school_id,
                        section_id=section_id,  # type: ignore[arg-type]
                        roll_number=roll_number,
                    )
                else:
                    exists = students_repository.find_student_duplicate_by_identity(
                        db,
                        school_id=school_id,
                        section_id=section_id,  # type: ignore[arg-type]
                        full_name_key=_normalize_key(full_name),
                        parent_phone=parent_phone,
                        date_of_birth=dob,
                    )
                if exists:
                    status = "duplicate"
                    errors.append("already_exists")

        row_out = StudentImportRowOut(
            row_number=idx,
            status=status,
            errors=errors,
            student_name=full_name,
            parent_phone=parent_phone_raw,
            class_name=class_name,
            section_name=section_name,
            roll_number=roll_number,
        )
        rows_out.append(row_out)

        if status == "valid":
            valid_payload_rows.append(
                {
                    "row_number": idx,
                    "name": name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": dob.isoformat() if dob else None,
                    "gender": gender,
                    "section_id": section_id,
                    "roll_number": roll_number,
                    "admission_date": admission_date.isoformat() if admission_date else None,
                    "parent_phone": parent_phone,
                    "parent_name": parent_name,
                }
            )

    valid_rows = sum(1 for row in rows_out if row.status == "valid")
    invalid_rows = sum(1 for row in rows_out if row.status == "invalid")
    duplicate_rows = sum(1 for row in rows_out if row.status == "duplicate")

    import_token: str | None = None
    if valid_payload_rows:
        token = uuid.uuid4().hex
        students_repository.create_import_batch(
            db,
            token=token,
            school_id=school_id,
            user_id=current_user.id,
            payload={
                "rows": valid_payload_rows,
                "total_rows": len(parsed_rows),
                "valid_rows": valid_rows,
                "invalid_rows": invalid_rows,
                "duplicate_rows": duplicate_rows,
            },
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=IMPORT_TTL_MINUTES),
        )
        import_token = token

    return StudentImportPreviewOut(
        import_token=import_token,
        total_rows=len(parsed_rows),
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        duplicate_rows=duplicate_rows,
        rows=rows_out,
    )


def commit_students_import(
    *,
    db: Session,
    school_id: int,
    current_user: User,
    payload: StudentImportCommitIn,
) -> StudentImportCommitOut:
    def _utc_now_comparable(value: datetime | None) -> datetime:
        now = datetime.now(timezone.utc)
        if value is None:
            return now
        if value.tzinfo is None:
            return now.replace(tzinfo=None)
        return now

    batch = students_repository.get_import_batch(
        db,
        import_token=payload.import_token,
        school_id=school_id,
        user_id=current_user.id,
    )
    if not batch:
        raise HTTPException(status_code=404, detail="import_token_not_found")
    if batch.is_committed:
        raise HTTPException(status_code=409, detail="import_already_committed")
    if batch.expires_at < _utc_now_comparable(batch.expires_at):
        raise HTTPException(status_code=410, detail="import_token_expired")

    rows = (batch.payload or {}).get("rows", [])
    created_rows = 0
    duplicate_rows = 0
    failed_rows = 0
    errors: list[StudentImportRowOut] = []
    tenant_code = get_tenant_code_for_school(db, school_id)

    for row in rows:
        row_number = int(row.get("row_number", 0))
        section_id = row.get("section_id")
        roll_number = row.get("roll_number")
        first_name = row.get("first_name")
        last_name = row.get("last_name")
        name = row.get("name")
        full_name = _resolve_full_name(first_name, last_name, name)
        parent_phone = row.get("parent_phone")

        section = students_repository.get_section_for_school(
            db,
            school_id=school_id,
            section_id=section_id,
        )
        if not section:
            failed_rows += 1
            errors.append(
                StudentImportRowOut(
                    row_number=row_number,
                    status="invalid",
                    errors=["section_not_found_at_commit"],
                    student_name=full_name,
                )
            )
            continue

        duplicate = None
        if roll_number:
            duplicate = students_repository.find_student_duplicate_by_roll_number(
                db,
                school_id=school_id,
                section_id=section_id,
                roll_number=str(roll_number),
            )
        else:
            duplicate = students_repository.find_student_duplicate_by_identity(
                db,
                school_id=school_id,
                section_id=section_id,
                full_name_key=_normalize_key(full_name),
                parent_phone=parent_phone,
                date_of_birth=date.fromisoformat(row["date_of_birth"])
                if row.get("date_of_birth")
                else None,
            )
        if duplicate:
            duplicate_rows += 1
            continue

        admission_date = date.fromisoformat(row["admission_date"]) if row.get("admission_date") else None
        admission_year = admission_date.year if admission_date else None
        student = Student(
            school_id=school_id,
            name=full_name or "",
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date.fromisoformat(row["date_of_birth"])
            if row.get("date_of_birth")
            else None,
            gender=row.get("gender"),
            section_id=section_id,
            roll_number=roll_number,
            admission_date=admission_date,
            parent_phone=parent_phone,
            parent_name=row.get("parent_name"),
            public_id=next_public_id(
                db,
                tenant_code=tenant_code,
                entity="student",
                display_year=admission_year,
            ),
        )
        db.add(student)
        created_rows += 1

    batch.is_committed = True
    batch.committed_at = datetime.now(timezone.utc)
    db.commit()

    return StudentImportCommitOut(
        total_rows=len(rows),
        created_rows=created_rows,
        duplicate_rows=duplicate_rows,
        failed_rows=failed_rows,
        errors=errors,
    )


def get_student_profile(*, db: Session, school_id: int, student_id: str) -> StudentProfileOut:
    student = students_repository.resolve_student_by_ref(
        db,
        school_id=school_id,
        student_ref=student_id,
    )
    if not student:
        raise HTTPException(status_code=404, detail="student_not_found")

    section, class_ = students_repository.get_section_and_class_for_student(
        db,
        school_id=school_id,
        section_id=student.section_id,
    )
    present_days = students_repository.count_attendance(
        db,
        school_id=school_id,
        student_id=student.id,
        attendance_status="present",
    )
    absent_days = students_repository.count_attendance(
        db,
        school_id=school_id,
        student_id=student.id,
        attendance_status="absent",
    )
    total_days = present_days + absent_days
    percentage = round((present_days / total_days) * 100, 2) if total_days else 0.0
    results = students_repository.list_recent_results(
        db,
        school_id=school_id,
        student_id=student.id,
        limit=3,
    )

    guardians: list[StudentGuardianOut] = []
    if student.parent_name or student.parent_phone:
        guardians.append(
            StudentGuardianOut(
                name=student.parent_name,
                relation="Parent",
                phone=student.parent_phone,
            )
        )

    return StudentProfileOut(
        id=student.id,
        student_code=student.public_id,
        public_id=student.public_id,
        name=student.name,
        class_id=class_.id if class_ else None,
        class_name=class_.name if class_ else None,
        section_id=section.id if section else None,
        section_name=section.name if section else None,
        status="active",
        personal_details=StudentPersonalDetails(
            date_of_birth=student.date_of_birth.isoformat() if student.date_of_birth else None,
            gender=student.gender,
        ),
        guardians=guardians,
        attendance=StudentAttendanceSummary(
            percentage=percentage,
            present_days=present_days,
            absent_days=absent_days,
            total_days=total_days,
        ),
        recent_results=[
            StudentRecentResult(
                subject_name=result.subject_name,
                exam_type=result.exam_type,
                marks_obtained=result.marks_obtained,
                max_marks=result.max_marks,
            )
            for result in results
        ],
    )


def get_student_report_card(
    *,
    db: Session,
    school_id: int,
    student_id: str,
) -> StudentReportCardOut:
    student = students_repository.resolve_student_by_ref(
        db,
        school_id=school_id,
        student_ref=student_id,
    )
    if not student:
        raise HTTPException(status_code=404, detail="student_not_found")

    section, class_ = students_repository.get_section_and_class_for_student(
        db,
        school_id=school_id,
        section_id=student.section_id,
    )
    present_days = students_repository.count_attendance(
        db,
        school_id=school_id,
        student_id=student.id,
        attendance_status="present",
    )
    absent_days = students_repository.count_attendance(
        db,
        school_id=school_id,
        student_id=student.id,
        attendance_status="absent",
    )
    total_days = present_days + absent_days
    attendance_percentage = round((present_days / total_days) * 100, 2) if total_days else 0.0

    marks_rows = students_repository.list_report_card_results(
        db,
        school_id=school_id,
        student_id=student.id,
    )
    rows: list[StudentReportCardRow] = []
    total_obtained = 0
    total_max = 0
    for result in marks_rows:
        percentage = round((result.marks_obtained / result.max_marks) * 100, 2) if result.max_marks else 0.0
        rows.append(
            StudentReportCardRow(
                subject_name=result.subject_name,
                exam_type=result.exam_type,
                marks_obtained=result.marks_obtained,
                max_marks=result.max_marks,
                percentage=percentage,
                grade=_grade_from_percentage(percentage),
            )
        )
        total_obtained += result.marks_obtained
        total_max += result.max_marks

    overall_percentage = round((total_obtained / total_max) * 100, 2) if total_max else 0.0
    return StudentReportCardOut(
        student_id=student.id,
        student_name=student.name,
        student_code=student.public_id,
        public_id=student.public_id,
        class_name=class_.name if class_ else None,
        section_name=section.name if section else None,
        attendance_percentage=attendance_percentage,
        present_days=present_days,
        absent_days=absent_days,
        total_days=total_days,
        total_obtained=total_obtained,
        total_max=total_max,
        overall_percentage=overall_percentage,
        overall_grade=_grade_from_percentage(overall_percentage),
        generated_at=datetime.now(timezone.utc).isoformat(),
        rows=rows,
    )
