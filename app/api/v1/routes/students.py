import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user, require_management, get_valid_school_id
from app.core.phone import normalize_phone
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.class_ import Class
from app.db.models.marks_record import MarksRecord
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.student_import_batch import StudentImportBatch
from app.db.models.subject import Subject
from app.db.models.user import User

router = APIRouter(prefix="/students", tags=["students"])
MAX_IMPORT_ROWS = 5000
IMPORT_TTL_MINUTES = 30

# --- SCHEMAS ---


class StudentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = None
    section_id: int | None = None
    roll_number: str | None = Field(default=None, min_length=1, max_length=32)
    admission_date: date | None = None
    parent_phone: str
    parent_name: str | None = None

    @model_validator(mode="after")
    def validate_name(self) -> "StudentCreate":
        if (self.name is None or self.name.strip() == "") and not (
            self.first_name and self.last_name
        ):
            raise ValueError("name_or_first_last_required")
        if self.name is not None:
            self.name = self.name.strip()
        if self.first_name is not None:
            self.first_name = self.first_name.strip()
        if self.last_name is not None:
            self.last_name = self.last_name.strip()
        return self


class StudentOut(BaseModel):
    id: int
    school_id: int
    student_code: str | None = None
    name: str
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    section_id: int | None = None
    section_name: str | None = None
    class_id: int | None = None
    class_name: str | None = None
    roll_number: str | None = None
    admission_date: date | None = None
    parent_phone: str
    parent_name: str | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StudentPersonalDetails(BaseModel):
    date_of_birth: str | None = None
    gender: str | None = None
    blood_group: str | None = None
    religion: str | None = None
    address: str | None = None


class StudentGuardianOut(BaseModel):
    name: str | None = None
    relation: str | None = None
    phone: str | None = None


class StudentAttendanceSummary(BaseModel):
    percentage: float
    present_days: int
    absent_days: int
    total_days: int


class StudentRecentResult(BaseModel):
    subject_name: str
    exam_type: str
    marks_obtained: int
    max_marks: int


class StudentProfileOut(BaseModel):
    id: int
    student_code: str
    name: str
    class_id: int | None
    class_name: str | None
    section_id: int | None
    section_name: str | None
    status: str
    personal_details: StudentPersonalDetails
    guardians: list[StudentGuardianOut]
    attendance: StudentAttendanceSummary
    recent_results: list[StudentRecentResult]


class StudentReportCardRow(BaseModel):
    subject_name: str
    exam_type: str
    marks_obtained: int
    max_marks: int
    percentage: float
    grade: str


class StudentReportCardOut(BaseModel):
    student_id: int
    student_name: str
    student_code: str
    class_name: str | None
    section_name: str | None
    attendance_percentage: float
    present_days: int
    absent_days: int
    total_days: int
    total_obtained: int
    total_max: int
    overall_percentage: float
    overall_grade: str
    generated_at: str
    rows: list[StudentReportCardRow]


class StudentImportRowOut(BaseModel):
    row_number: int
    status: Literal["valid", "invalid", "duplicate"]
    errors: list[str] = Field(default_factory=list)
    student_name: str | None = None
    parent_phone: str | None = None
    class_name: str | None = None
    section_name: str | None = None
    roll_number: str | None = None


class StudentImportPreviewOut(BaseModel):
    import_token: str | None = None
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    rows: list[StudentImportRowOut]


class StudentImportCommitIn(BaseModel):
    import_token: str
    mode: Literal["skip_duplicates"] = "skip_duplicates"


class StudentImportCommitOut(BaseModel):
    total_rows: int
    created_rows: int
    duplicate_rows: int
    failed_rows: int
    errors: list[StudentImportRowOut] = Field(default_factory=list)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_key(value: str | None) -> str:
    return (value or "").strip().lower()


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


def _resolve_full_name(first_name: str | None, last_name: str | None, name: str | None) -> str | None:
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


# --- ROUTES ---

@router.get("", response_model=List[StudentOut])
def list_students(
    section_id: int | None = Query(None),
    db: Session = Depends(get_db),
    # Use school_id validation to ensure isolation and permission check
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
):
    """
    Lists students for a specific school and optionally filters by section.
    """
    q = (
        db.query(Student, Section, Class)
        .outerjoin(Section, (Section.id == Student.section_id))
        .outerjoin(Class, (Class.id == Section.class_id))
        .filter(Student.school_id == school_id)
    )

    if section_id:
        q = q.filter(Student.section_id == section_id)

    rows = q.order_by(Student.id.asc()).all()

    return [
        StudentOut(
            id=student.id,
            school_id=student.school_id,
            student_code=f"ST-{student.id:04d}",
            name=student.name,
            first_name=student.first_name,
            last_name=student.last_name,
            date_of_birth=student.date_of_birth,
            gender=student.gender,
            section_id=student.section_id,
            section_name=section.name if section else None,
            class_id=class_.id if class_ else None,
            class_name=class_.name if class_ else None,
            roll_number=student.roll_number,
            admission_date=student.admission_date,
            parent_phone=student.parent_phone,
            parent_name=student.parent_name,
            status="active",
        )
        for student, section, class_ in rows
    ]


@router.post("", response_model=StudentOut, status_code=201)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    # Force validation of the school where the student is being created
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
):
    """Only management can create students within their school context."""
    if payload.section_id is not None:
        sec = (
            db.query(Section)
            .filter(
                Section.id == payload.section_id,
                Section.school_id == school_id,
            )
            .first()
        )
        if not sec:
            raise HTTPException(status_code=400, detail="invalid_section_id")

    full_name = (
        payload.name
        if payload.name and payload.name.strip()
        else f"{payload.first_name} {payload.last_name}".strip()
    )

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
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.post("/import/preview", response_model=StudentImportPreviewOut)
async def preview_students_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
):
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

    sections = (
        db.query(Section, Class)
        .join(Class, Class.id == Section.class_id)
        .filter(Section.school_id == school_id, Class.school_id == school_id)
        .all()
    )
    section_map: dict[tuple[str, str], int] = {
        (_normalize_key(cls.name), _normalize_key(sec.name)): sec.id
        for sec, cls in sections
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
        raise HTTPException(
            status_code=400,
            detail=f"max_{MAX_IMPORT_ROWS}_rows_allowed",
        )

    for idx, raw in enumerate(parsed_rows, start=2):
        normalized_row = {
            _normalize_key(k).replace(" ", "_"): v
            for k, v in (raw or {}).items()
            if k is not None
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
            pick(normalized_row, "admission_date"), "admission_date", errors
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
                (_normalize_key(class_name), _normalize_key(section_name))
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
                    exists = (
                        db.query(Student.id)
                        .filter(
                            Student.school_id == school_id,
                            Student.section_id == section_id,
                            func.lower(Student.roll_number) == roll_number.lower(),
                        )
                        .first()
                    )
                else:
                    exists_query = db.query(Student.id).filter(
                        Student.school_id == school_id,
                        Student.section_id == section_id,
                        func.lower(Student.name) == _normalize_key(full_name),
                        Student.parent_phone == parent_phone,
                    )
                    if dob is None:
                        exists_query = exists_query.filter(Student.date_of_birth.is_(None))
                    else:
                        exists_query = exists_query.filter(Student.date_of_birth == dob)
                    exists = exists_query.first()

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
        batch = StudentImportBatch(
            id=token,
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
        db.add(batch)
        db.commit()
        import_token = token

    return StudentImportPreviewOut(
        import_token=import_token,
        total_rows=len(parsed_rows),
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        duplicate_rows=duplicate_rows,
        rows=rows_out,
    )


@router.post("/import/commit", response_model=StudentImportCommitOut)
def commit_students_import(
    payload: StudentImportCommitIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
):
    batch = (
        db.query(StudentImportBatch)
        .filter(
            StudentImportBatch.id == payload.import_token,
            StudentImportBatch.school_id == school_id,
            StudentImportBatch.user_id == current_user.id,
        )
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="import_token_not_found")
    if batch.is_committed:
        raise HTTPException(status_code=409, detail="import_already_committed")
    if batch.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="import_token_expired")

    rows = (batch.payload or {}).get("rows", [])
    created_rows = 0
    duplicate_rows = 0
    failed_rows = 0
    errors: list[StudentImportRowOut] = []

    for row in rows:
        row_number = int(row.get("row_number", 0))
        section_id = row.get("section_id")
        roll_number = row.get("roll_number")
        first_name = row.get("first_name")
        last_name = row.get("last_name")
        name = row.get("name")
        full_name = _resolve_full_name(first_name, last_name, name)
        parent_phone = row.get("parent_phone")

        sec = (
            db.query(Section.id)
            .filter(Section.id == section_id, Section.school_id == school_id)
            .first()
        )
        if not sec:
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
            duplicate = (
                db.query(Student.id)
                .filter(
                    Student.school_id == school_id,
                    Student.section_id == section_id,
                    func.lower(Student.roll_number) == str(roll_number).lower(),
                )
                .first()
            )
        else:
            duplicate_query = db.query(Student.id).filter(
                Student.school_id == school_id,
                Student.section_id == section_id,
                func.lower(Student.name) == _normalize_key(full_name),
                Student.parent_phone == parent_phone,
            )
            if row.get("date_of_birth"):
                duplicate_query = duplicate_query.filter(
                    Student.date_of_birth == date.fromisoformat(row["date_of_birth"])
                )
            else:
                duplicate_query = duplicate_query.filter(Student.date_of_birth.is_(None))
            duplicate = duplicate_query.first()
        if duplicate:
            duplicate_rows += 1
            continue

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
            admission_date=date.fromisoformat(row["admission_date"])
            if row.get("admission_date")
            else None,
            parent_phone=parent_phone,
            parent_name=row.get("parent_name"),
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


@router.get("/{student_id}", response_model=StudentProfileOut)
def get_student_profile(
    student_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
):
    """Retrieves detailed student profile including attendance and marks."""
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == school_id,
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="student_not_found")

    section = None
    class_ = None
    if student.section_id is not None:
        section = (
            db.query(Section)
            .filter(
                Section.id == student.section_id,
                Section.school_id == school_id,
            )
            .first()
        )
        if section:
            class_ = (
                db.query(Class)
                .filter(
                    Class.id == section.class_id,
                    Class.school_id == school_id,
                )
                .first()
            )

    present_days = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == "present",
        )
        .scalar()
        or 0
    )
    absent_days = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == "absent",
        )
        .scalar()
        or 0
    )
    total_days = present_days + absent_days
    percentage = round((present_days / total_days) *
                       100, 2) if total_days else 0.0

    results = (
        db.query(
            MarksRecord.exam_type,
            MarksRecord.marks_obtained,
            MarksRecord.max_marks,
            Subject.name.label("subject_name"),
        )
        .join(
            Subject,
            (Subject.id == MarksRecord.subject_id)
            & (Subject.school_id == school_id),
        )
        .filter(
            MarksRecord.school_id == school_id,
            MarksRecord.student_id == student_id,
        )
        .order_by(MarksRecord.created_at.desc())
        .limit(3)
        .all()
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
        student_code=f"ST-{student.id:04d}",
        name=student.name,
        class_id=class_.id if class_ else None,
        class_name=class_.name if class_ else None,
        section_id=section.id if section else None,
        section_name=section.name if section else None,
        status="active",
        personal_details=StudentPersonalDetails(
            date_of_birth=student.date_of_birth.isoformat()
            if student.date_of_birth
            else None,
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
                subject_name=r.subject_name,
                exam_type=r.exam_type,
                marks_obtained=r.marks_obtained,
                max_marks=r.max_marks,
            )
            for r in results
        ],
    )


@router.get("/{student_id}/report-card", response_model=StudentReportCardOut)
def get_student_report_card(
    student_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
):
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == school_id,
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="student_not_found")

    section = None
    class_ = None
    if student.section_id is not None:
        section = (
            db.query(Section)
            .filter(
                Section.id == student.section_id,
                Section.school_id == school_id,
            )
            .first()
        )
        if section:
            class_ = (
                db.query(Class)
                .filter(
                    Class.id == section.class_id,
                    Class.school_id == school_id,
                )
                .first()
            )

    present_days = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == "present",
        )
        .scalar()
        or 0
    )
    absent_days = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == "absent",
        )
        .scalar()
        or 0
    )
    total_days = present_days + absent_days
    attendance_percentage = round((present_days / total_days) * 100, 2) if total_days else 0.0

    marks_rows = (
        db.query(
            MarksRecord.exam_type,
            MarksRecord.marks_obtained,
            MarksRecord.max_marks,
            Subject.name.label("subject_name"),
        )
        .join(
            Subject,
            (Subject.id == MarksRecord.subject_id)
            & (Subject.school_id == school_id),
        )
        .filter(
            MarksRecord.school_id == school_id,
            MarksRecord.student_id == student_id,
        )
        .order_by(Subject.name.asc(), MarksRecord.created_at.desc())
        .all()
    )

    rows: list[StudentReportCardRow] = []
    total_obtained = 0
    total_max = 0
    for r in marks_rows:
        percentage = round((r.marks_obtained / r.max_marks) * 100, 2) if r.max_marks else 0.0
        rows.append(
            StudentReportCardRow(
                subject_name=r.subject_name,
                exam_type=r.exam_type,
                marks_obtained=r.marks_obtained,
                max_marks=r.max_marks,
                percentage=percentage,
                grade=_grade_from_percentage(percentage),
            )
        )
        total_obtained += r.marks_obtained
        total_max += r.max_marks

    overall_percentage = round((total_obtained / total_max) * 100, 2) if total_max else 0.0

    return StudentReportCardOut(
        student_id=student.id,
        student_name=student.name,
        student_code=f"ST-{student.id:04d}",
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
