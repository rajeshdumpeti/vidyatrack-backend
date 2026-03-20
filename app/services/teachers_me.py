from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.schemas.teachers_me import (
    TeacherAttendanceSectionOut,
    TeacherContextOut,
    TeacherContextSubjectOut,
    TeacherMeOut,
    TeacherReadinessOut,
    TeachingAssignmentOut,
)
from app.db.models.class_ import Class
from app.db.models.school import School
from app.db.models.section import Section
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.student import Student
from app.db.models.subject import Subject
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def _get_teacher_or_404(db: Session, *, user_id: int) -> Teacher:
    teacher = db.query(Teacher).filter(Teacher.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")
    return teacher


def get_my_teacher_profile(*, db: Session, current_user: User) -> TeacherMeOut:
    teacher = _get_teacher_or_404(db, user_id=current_user.id)
    return TeacherMeOut(
        teacher_id=teacher.id,
        school_id=teacher.school_id,
        name=teacher.name,
        email=current_user.email,
        phone=current_user.phone,
    )


def get_my_teacher_context(*, db: Session, school_id: int, current_user: User) -> TeacherContextOut:
    teacher = _get_teacher_or_404(db, user_id=current_user.id)
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
        .join(TeacherPrimarySection, TeacherPrimarySection.section_id == Section.id)
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


def get_my_teaching_assignments(*, db: Session, current_user: User) -> list[TeachingAssignmentOut]:
    teacher = _get_teacher_or_404(db, user_id=current_user.id)
    school_id = teacher.school_id
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
            SectionSubjectTeacher.school_id == school_id,
        )
        .all()
    )
    return [TeachingAssignmentOut(**row._asdict()) for row in rows]


def get_my_attendance_section(*, db: Session, current_user: User) -> TeacherAttendanceSectionOut:
    teacher = _get_teacher_or_404(db, user_id=current_user.id)
    school_id = teacher.school_id
    mapping = (
        db.query(TeacherPrimarySection)
        .filter(
            TeacherPrimarySection.teacher_id == teacher.id,
            TeacherPrimarySection.school_id == school_id,
        )
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=404, detail="no_primary_section_assigned")

    result = (
        db.query(
            Section.id.label("section_id"),
            Section.name.label("section_name"),
            Class.id.label("class_id"),
            Class.name.label("class_name"),
        )
        .join(Class, Class.id == Section.class_id)
        .filter(Section.id == mapping.section_id, Section.school_id == school_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="section_details_not_found")

    return TeacherAttendanceSectionOut(
        school_id=school_id,
        section_id=result.section_id,
        section_name=result.section_name,
        class_id=result.class_id,
        class_name=result.class_name,
    )


def get_my_teacher_readiness(*, db: Session, current_user: User) -> TeacherReadinessOut:
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

    school_id = teacher.school_id
    mapping = (
        db.query(UserSchool)
        .filter(UserSchool.user_id == current_user.id, UserSchool.school_id == school_id)
        .first()
    )
    primary = (
        db.query(TeacherPrimarySection)
        .filter(
            TeacherPrimarySection.teacher_id == teacher.id,
            TeacherPrimarySection.school_id == school_id,
        )
        .first()
    )
    assignment_count = (
        db.query(SectionSubjectTeacher)
        .filter(
            SectionSubjectTeacher.teacher_id == teacher.id,
            SectionSubjectTeacher.school_id == school_id,
        )
        .count()
    )
    student_count = 0
    if primary:
        student_count = (
            db.query(Student)
            .filter(
                Student.school_id == school_id,
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
        status_value = "ready"
        next_action = None
    else:
        status_value = missing[0]
        if status_value == "needs_school_mapping":
            next_action = "Ask management to map your account to this school."
        elif status_value == "needs_primary_section":
            next_action = "Ask management to set your primary section."
        elif status_value == "needs_subject_assignment":
            next_action = "Ask management to assign at least one subject."
        else:
            next_action = "Ask management to add students to your section."

    return TeacherReadinessOut(
        status=status_value,
        school_id=school_id,
        teacher_id=teacher.id,
        section_id=primary.section_id if primary else None,
        checks=checks,
        missing_requirements=missing,
        recommended_next_action=next_action,
    )
