from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_valid_school_id, require_teacher
from app.db.models.school import School
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.section import Section
from app.db.models.class_ import Class
from app.db.models.subject import Subject
from app.db.models.student import Student
from app.db.models.user import User
from app.db.models.user_school import UserSchool

router = APIRouter(prefix="/teachers/me", tags=["teachers-me"])

# --- SCHEMAS ---


class TeacherMeOut(BaseModel):
    teacher_id: int
    school_id: int
    name: str
    email: str | None = None
    phone: str | None = None


class TeachingAssignmentOut(BaseModel):
    school_id: int
    section_id: int
    section_name: str
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str


class TeacherAttendanceSectionOut(BaseModel):
    school_id: int
    section_id: int
    section_name: str
    class_id: int
    class_name: str


class TeacherContextSubjectOut(BaseModel):
    subject_id: int
    subject_name: str


class TeacherContextOut(BaseModel):
    teacher_id: int
    user_id: int
    school_id: int
    school_name: str
    class_id: int | None = None
    class_name: str | None = None
    section_id: int | None = None
    section_name: str | None = None
    subjects: list[TeacherContextSubjectOut]


class TeacherReadinessOut(BaseModel):
    status: str
    school_id: int | None = None
    teacher_id: int | None = None
    section_id: int | None = None
    checks: dict[str, bool]
    missing_requirements: list[str]
    recommended_next_action: str | None = None

# --- ROUTES ---


@router.get("", response_model=TeacherMeOut)
def get_my_teacher_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    # Lookup the teacher record via the User ID
    teacher = db.query(Teacher).filter(
        Teacher.user_id == current_user.id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    return TeacherMeOut(
        teacher_id=teacher.id,
        school_id=teacher.school_id,
        name=teacher.name,
        email=current_user.email,
        phone=current_user.phone,
    )


@router.get("/context", response_model=TeacherContextOut)
def get_my_teacher_context(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_teacher),
):
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    if teacher.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="teacher_not_assigned_to_school",
        )

    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="school_not_found")

    primary = (
        db.query(
            Section.id.label("section_id"),
            Section.name.label("section_name"),
            Class.id.label("class_id"),
            Class.name.label("class_name"),
        )
        .join(
            TeacherPrimarySection,
            TeacherPrimarySection.section_id == Section.id,
        )
        .join(Class, Class.id == Section.class_id)
        .filter(
            TeacherPrimarySection.teacher_id == teacher.id,
            TeacherPrimarySection.school_id == school_id,
            Section.school_id == school_id,
        )
        .first()
    )

    subject_rows = (
        db.query(
            Subject.id.label("subject_id"),
            Subject.name.label("subject_name"),
        )
        .join(SectionSubjectTeacher, SectionSubjectTeacher.subject_id == Subject.id)
        .filter(
            SectionSubjectTeacher.teacher_id == teacher.id,
            SectionSubjectTeacher.school_id == school_id,
        )
        .order_by(Subject.name.asc())
        .all()
    )

    return TeacherContextOut(
        teacher_id=teacher.id,
        user_id=current_user.id,
        school_id=school_id,
        school_name=school.name,
        class_id=primary.class_id if primary else None,
        class_name=primary.class_name if primary else None,
        section_id=primary.section_id if primary else None,
        section_name=primary.section_name if primary else None,
        subjects=[TeacherContextSubjectOut(**row._asdict()) for row in subject_rows],
    )


@router.get("/teaching-assignments", response_model=list[TeachingAssignmentOut])
def get_my_teaching_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    # Find teacher to get their school context (sid)
    teacher = db.query(Teacher).filter(
        Teacher.user_id == current_user.id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    sid = teacher.school_id

    # JOIN assignments with Section, Class, and Subject for the UI labels
    rows = (
        db.query(
            SectionSubjectTeacher.school_id,
            SectionSubjectTeacher.section_id,
            Section.name.label("section_name"),
            Class.id.label("class_id"),
            Class.name.label("class_name"),
            SectionSubjectTeacher.subject_id,
            Subject.name.label("subject_name"),
        )
        .join(Section, Section.id == SectionSubjectTeacher.section_id)
        .join(Class, Class.id == Section.class_id)
        .join(Subject, Subject.id == SectionSubjectTeacher.subject_id)
        .filter(
            SectionSubjectTeacher.teacher_id == teacher.id,
            SectionSubjectTeacher.school_id == sid
        )
        .all()
    )
    return [TeachingAssignmentOut(**r._asdict()) for r in rows]


@router.get("/attendance-section", response_model=TeacherAttendanceSectionOut)
def get_my_attendance_section(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    teacher = db.query(Teacher).filter(
        Teacher.user_id == current_user.id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    sid = teacher.school_id

    # Find the primary section for the "Mark Attendance" button context
    mapping = db.query(TeacherPrimarySection).filter(
        TeacherPrimarySection.teacher_id == teacher.id,
        TeacherPrimarySection.school_id == sid
    ).first()

    if not mapping:
        raise HTTPException(
            status_code=404, detail="no_primary_section_assigned")

    res = (
        db.query(
            Section.id.label("section_id"),
            Section.name.label("section_name"),
            Class.id.label("class_id"),
            Class.name.label("class_name")
        )
        .join(Class, Class.id == Section.class_id)
        .filter(Section.id == mapping.section_id, Section.school_id == sid)
        .first()
    )

    if not res:
        raise HTTPException(
            status_code=404, detail="section_details_not_found")

    return TeacherAttendanceSectionOut(
        school_id=sid,
        section_id=res.section_id,
        section_name=res.section_name,
        class_id=res.class_id,
        class_name=res.class_name
    )


@router.get("/readiness", response_model=TeacherReadinessOut)
def get_my_teacher_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    if not teacher:
        return TeacherReadinessOut(
            status="needs_teacher_profile",
            checks={
                "has_teacher_profile": False,
                "has_school_mapping": False,
                "has_primary_section": False,
                "has_subject_assignments": False,
                "has_students_in_primary_section": False,
            },
            missing_requirements=["needs_teacher_profile"],
            recommended_next_action="Ask management to create teacher profile.",
        )

    sid = teacher.school_id
    mapping = (
        db.query(UserSchool)
        .filter(UserSchool.user_id == current_user.id, UserSchool.school_id == sid)
        .first()
    )
    primary = (
        db.query(TeacherPrimarySection)
        .filter(
            TeacherPrimarySection.teacher_id == teacher.id,
            TeacherPrimarySection.school_id == sid,
        )
        .first()
    )
    assignment_count = (
        db.query(SectionSubjectTeacher)
        .filter(
            SectionSubjectTeacher.teacher_id == teacher.id,
            SectionSubjectTeacher.school_id == sid,
        )
        .count()
    )
    student_count = 0
    if primary:
        student_count = (
            db.query(Student)
            .filter(
                Student.school_id == sid,
                Student.section_id == primary.section_id,
            )
            .count()
        )

    checks = {
        "has_teacher_profile": True,
        "has_school_mapping": mapping is not None,
        "has_primary_section": primary is not None,
        "has_subject_assignments": assignment_count > 0,
        "has_students_in_primary_section": student_count > 0 if primary else False,
    }

    missing: list[str] = []
    if not checks["has_school_mapping"]:
        missing.append("needs_school_mapping")
    if not checks["has_primary_section"]:
        missing.append("needs_primary_section")
    if not checks["has_subject_assignments"]:
        missing.append("needs_subject_assignment")
    if checks["has_primary_section"] and not checks["has_students_in_primary_section"]:
        missing.append("needs_students")

    if not missing:
        status = "ready"
        next_action = None
    else:
        status = missing[0]
        if status == "needs_school_mapping":
            next_action = "Ask management to map your account to this school."
        elif status == "needs_primary_section":
            next_action = "Ask management to set your primary section."
        elif status == "needs_subject_assignment":
            next_action = "Ask management to assign at least one subject."
        else:
            next_action = "Ask management to add students to your section."

    return TeacherReadinessOut(
        status=status,
        school_id=sid,
        teacher_id=teacher.id,
        section_id=primary.section_id if primary else None,
        checks=checks,
        missing_requirements=missing,
        recommended_next_action=next_action,
    )
