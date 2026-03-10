from __future__ import annotations

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.v1.schemas.communications import (
    HomeworkCreate,
    HomeworkOut,
    ParentMessageCreate,
    ParentMessageOut,
)
from app.core.roles import normalize_role
from app.db.models.homework_broadcast import HomeworkBroadcast
from app.db.models.parent_message import ParentMessage
from app.db.models.parent_message_recipient import ParentMessageRecipient
from app.db.models.section import Section
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.student import Student
from app.db.models.subject import Subject
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.user import User


def _get_teacher_or_404(db: Session, school_id: int, user_id: int) -> Teacher:
    teacher = (
        db.query(Teacher)
        .filter(Teacher.school_id == school_id, Teacher.user_id == user_id)
        .first()
    )
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")
    return teacher


def _ensure_section_in_school(db: Session, school_id: int, section_id: int) -> None:
    exists = (
        db.query(Section.id)
        .filter(Section.school_id == school_id, Section.id == section_id)
        .first()
    )
    if not exists:
        raise HTTPException(status_code=400, detail="invalid_section_id")


def _ensure_teacher_assigned_to_section_subject(
    db: Session,
    school_id: int,
    teacher_id: int,
    section_id: int,
    subject_id: int,
) -> None:
    assigned = (
        db.query(SectionSubjectTeacher.id)
        .filter(
            SectionSubjectTeacher.school_id == school_id,
            SectionSubjectTeacher.teacher_id == teacher_id,
            SectionSubjectTeacher.section_id == section_id,
            SectionSubjectTeacher.subject_id == subject_id,
        )
        .first()
    )
    if not assigned:
        raise HTTPException(status_code=403, detail="not_assigned_to_section_subject")


def _ensure_teacher_assigned_to_section(
    db: Session,
    school_id: int,
    teacher_id: int,
    section_id: int,
) -> None:
    assigned = (
        db.query(SectionSubjectTeacher.id)
        .filter(
            SectionSubjectTeacher.school_id == school_id,
            SectionSubjectTeacher.teacher_id == teacher_id,
            SectionSubjectTeacher.section_id == section_id,
        )
        .first()
    )
    if assigned:
        return

    primary = (
        db.query(TeacherPrimarySection.id)
        .filter(
            TeacherPrimarySection.school_id == school_id,
            TeacherPrimarySection.teacher_id == teacher_id,
            TeacherPrimarySection.section_id == section_id,
        )
        .first()
    )
    if not primary:
        raise HTTPException(status_code=403, detail="not_assigned_to_section")


def create_homework(
    *,
    payload: HomeworkCreate,
    db: Session,
    current_user: User,
    school_id: int,
) -> HomeworkOut:
    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="title_required")
    if not payload.description.strip():
        raise HTTPException(status_code=422, detail="description_required")

    _ensure_section_in_school(db, school_id, payload.section_id)
    is_teacher = normalize_role(current_user.role) == "TEACHER"
    if is_teacher:
        teacher = _get_teacher_or_404(db, school_id, current_user.id)
        _ensure_teacher_assigned_to_section_subject(
            db,
            school_id,
            teacher.id,
            payload.section_id,
            payload.subject_id,
        )
    else:
        subject = (
            db.query(Subject.id)
            .filter(Subject.school_id == school_id, Subject.id == payload.subject_id)
            .first()
        )
        if not subject:
            raise HTTPException(status_code=400, detail="invalid_subject_id")

    row = HomeworkBroadcast(
        school_id=school_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        due_date=payload.due_date,
        created_by_user_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return HomeworkOut(
        id=row.id,
        school_id=row.school_id,
        section_id=row.section_id,
        subject_id=row.subject_id,
        title=row.title,
        description=row.description,
        due_date=row.due_date,
        created_by=row.created_by_user_id,
        created_at=row.created_at,
    )


def list_homework(
    *,
    school_id: int,
    section_id: int | None,
    subject_id: int | None,
    db: Session,
    current_user: User,
) -> list[HomeworkOut]:
    if subject_id is not None and section_id is None:
        raise HTTPException(status_code=422, detail="section_id_required_for_subject")

    if section_id is not None:
        _ensure_section_in_school(db, school_id, section_id)
        if subject_id is not None:
            subject = (
                db.query(Subject.id)
                .filter(Subject.school_id == school_id, Subject.id == subject_id)
                .first()
            )
            if not subject:
                raise HTTPException(status_code=400, detail="invalid_subject_id")

    query = db.query(HomeworkBroadcast).filter(HomeworkBroadcast.school_id == school_id)
    if section_id is not None:
        query = query.filter(HomeworkBroadcast.section_id == section_id)
        if subject_id is not None:
            query = query.filter(HomeworkBroadcast.subject_id == subject_id)
    else:
        if normalize_role(current_user.role) == "TEACHER":
            query = query.filter(HomeworkBroadcast.created_by_user_id == current_user.id)

    rows = query.order_by(HomeworkBroadcast.created_at.desc()).all()
    return [
        HomeworkOut(
            id=row.id,
            school_id=row.school_id,
            section_id=row.section_id,
            subject_id=row.subject_id,
            title=row.title,
            description=row.description,
            due_date=row.due_date,
            created_by=row.created_by_user_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def create_parent_message(
    *,
    payload: ParentMessageCreate,
    db: Session,
    current_user: User,
    school_id: int,
) -> ParentMessageOut:
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="message_required")

    _ensure_section_in_school(db, school_id, payload.section_id)
    if normalize_role(current_user.role) == "TEACHER":
        teacher = _get_teacher_or_404(db, school_id, current_user.id)
        _ensure_teacher_assigned_to_section(db, school_id, teacher.id, payload.section_id)

    unique_student_ids = list(dict.fromkeys(payload.student_ids))
    students = (
        db.query(Student.id)
        .filter(
            Student.school_id == school_id,
            Student.section_id == payload.section_id,
            Student.id.in_(unique_student_ids),
        )
        .all()
    )
    if len(students) != len(unique_student_ids):
        raise HTTPException(status_code=400, detail="invalid_student_ids")

    message = ParentMessage(
        school_id=school_id,
        section_id=payload.section_id,
        subject=payload.subject.strip() if payload.subject else None,
        message=payload.message.strip(),
        created_by_user_id=current_user.id,
    )
    db.add(message)
    db.flush()

    for student_id in unique_student_ids:
        db.add(ParentMessageRecipient(message_id=message.id, student_id=student_id))

    db.commit()
    db.refresh(message)

    return ParentMessageOut(
        id=message.id,
        message_id=message.id,
        school_id=message.school_id,
        section_id=message.section_id,
        subject=message.subject,
        message=message.message,
        student_ids=unique_student_ids,
        delivered_count=len(unique_student_ids),
        created_by=message.created_by_user_id,
        created_at=message.created_at,
    )


def list_parent_messages(
    *,
    school_id: int,
    section_id: int | None,
    db: Session,
    current_user: User,
) -> list[ParentMessageOut]:
    if section_id is not None:
        _ensure_section_in_school(db, school_id, section_id)

    query = db.query(ParentMessage).filter(ParentMessage.school_id == school_id)
    if section_id is not None:
        query = query.filter(ParentMessage.section_id == section_id)
    else:
        if normalize_role(current_user.role) == "TEACHER":
            query = query.filter(ParentMessage.created_by_user_id == current_user.id)

    messages = query.order_by(ParentMessage.created_at.desc()).all()
    if not messages:
        return []

    message_ids = [message.id for message in messages]
    recipients = (
        db.query(ParentMessageRecipient)
        .filter(ParentMessageRecipient.message_id.in_(message_ids))
        .all()
    )
    recipients_by_message: dict[int, list[int]] = {}
    for recipient in recipients:
        recipients_by_message.setdefault(recipient.message_id, []).append(recipient.student_id)

    return [
        ParentMessageOut(
            id=message.id,
            message_id=message.id,
            school_id=message.school_id,
            section_id=message.section_id,
            subject=message.subject,
            message=message.message,
            student_ids=recipients_by_message.get(message.id, []),
            delivered_count=len(recipients_by_message.get(message.id, [])),
            created_by=message.created_by_user_id,
            created_at=message.created_at,
        )
        for message in messages
    ]
