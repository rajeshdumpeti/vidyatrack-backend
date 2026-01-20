from typing import List

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.class_ import Class
from app.db.models.marks_record import MarksRecord
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.subject import Subject

router = APIRouter(prefix="/students", tags=["students"])


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

    class Config:
        from_attributes = True


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


@router.get("", response_model=List[StudentOut])
def list_students(
    section_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    school_id = current_user["school_id"]
    q = (
        db.query(Student, Section, Class)
        .outerjoin(
            Section,
            (Section.id == Student.section_id) & (Section.school_id == school_id),
        )
        .outerjoin(
            Class,
            (Class.id == Section.class_id) & (Class.school_id == school_id),
        )
        .filter(Student.school_id == school_id)
    )

    if section_id is not None:
        sec = (
            db.query(Section)
            .filter(
                Section.id == section_id,
                Section.school_id == school_id,
            )
            .first()
        )
        if not sec:
            raise HTTPException(status_code=400, detail="invalid_section_id")

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
    current_user: dict = Depends(get_current_user),
):
    if payload.section_id is not None:
        sec = (
            db.query(Section)
            .filter(
                Section.id == payload.section_id,
                Section.school_id == current_user["school_id"],
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
        school_id=current_user["school_id"],
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
    return StudentOut(
        id=student.id,
        school_id=student.school_id,
        student_code=f"ST-{student.id:04d}",
        name=student.name,
        first_name=student.first_name,
        last_name=student.last_name,
        date_of_birth=student.date_of_birth,
        gender=student.gender,
        section_id=student.section_id,
        section_name=None,
        class_id=None,
        class_name=None,
        roll_number=student.roll_number,
        admission_date=student.admission_date,
        parent_phone=student.parent_phone,
        parent_name=student.parent_name,
        status="active",
    )


@router.get("/{student_id}", response_model=StudentProfileOut)
def get_student_profile(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user["school_id"],
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
                Section.school_id == current_user["school_id"],
            )
            .first()
        )
        if section:
            class_ = (
                db.query(Class)
                .filter(
                    Class.id == section.class_id,
                    Class.school_id == current_user["school_id"],
                )
                .first()
            )

    present_days = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == current_user["school_id"],
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == "present",
        )
        .scalar()
        or 0
    )
    absent_days = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == current_user["school_id"],
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == "absent",
        )
        .scalar()
        or 0
    )
    total_days = present_days + absent_days
    percentage = round((present_days / total_days) * 100, 2) if total_days else 0.0

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
            & (Subject.school_id == current_user["school_id"]),
        )
        .filter(
            MarksRecord.school_id == current_user["school_id"],
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
