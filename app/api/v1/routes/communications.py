from datetime import date, datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_valid_school_id, require_teacher_or_principal
from app.db.models.homework_broadcast import HomeworkBroadcast
from app.db.models.parent_message import ParentMessage
from app.db.models.parent_message_recipient import ParentMessageRecipient
from app.db.models.section import Section
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.subject import Subject
from app.core.roles import normalize_role

router = APIRouter(prefix="/communications", tags=["communications"])


class HomeworkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: int
    subject_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    due_date: date | None = None


class HomeworkOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    title: str
    description: str
    due_date: date | None
    created_by: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParentMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: int
    student_ids: List[int] = Field(min_length=1)
    message: str = Field(min_length=1)
    subject: str | None = Field(default=None, max_length=200)


class ParentMessageOut(BaseModel):
    id: int
    message_id: int
    school_id: int
    section_id: int
    subject: str | None = None
    message: str
    student_ids: List[int]
    delivered_count: int
    created_by: int | None
    created_at: datetime


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
    db: Session, school_id: int, teacher_id: int, section_id: int, subject_id: int
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
    db: Session, school_id: int, teacher_id: int, section_id: int
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


@router.post("/homework", response_model=HomeworkOut, status_code=201)
def create_homework(
    payload: HomeworkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher_or_principal),
    school_id: int = Depends(get_valid_school_id),
):
    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="title_required")
    if not payload.description.strip():
        raise HTTPException(status_code=422, detail="description_required")

    _ensure_section_in_school(db, school_id, payload.section_id)
    is_teacher = normalize_role(current_user.role) == "TEACHER"
    if is_teacher:
        teacher = _get_teacher_or_404(db, school_id, current_user.id)
        _ensure_teacher_assigned_to_section_subject(
            db, school_id, teacher.id, payload.section_id, payload.subject_id
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


@router.get("/homework", response_model=List[HomeworkOut])
def list_homework(
    school_id: int = Depends(get_valid_school_id),
    section_id: int | None = Query(None),
    subject_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher_or_principal),
):
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

    q = db.query(HomeworkBroadcast).filter(HomeworkBroadcast.school_id == school_id)

    if section_id is not None:
        q = q.filter(HomeworkBroadcast.section_id == section_id)
        if subject_id is not None:
            q = q.filter(HomeworkBroadcast.subject_id == subject_id)
    else:
        is_teacher = normalize_role(current_user.role) == "TEACHER"
        if is_teacher:
            # No section filter: return only the teacher's own history
            q = q.filter(HomeworkBroadcast.created_by_user_id == current_user.id)

    rows = q.order_by(HomeworkBroadcast.created_at.desc()).all()
    return [
        HomeworkOut(
            id=r.id,
            school_id=r.school_id,
            section_id=r.section_id,
            subject_id=r.subject_id,
            title=r.title,
            description=r.description,
            due_date=r.due_date,
            created_by=r.created_by_user_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/parent-messages", response_model=ParentMessageOut, status_code=201)
def create_parent_message(
    payload: ParentMessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher_or_principal),
    school_id: int = Depends(get_valid_school_id),
):
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="message_required")

    _ensure_section_in_school(db, school_id, payload.section_id)
    is_teacher = normalize_role(current_user.role) == "TEACHER"
    if is_teacher:
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

    msg = ParentMessage(
        school_id=school_id,
        section_id=payload.section_id,
        subject=payload.subject.strip() if payload.subject else None,
        message=payload.message.strip(),
        created_by_user_id=current_user.id,
    )
    db.add(msg)
    db.flush()

    for sid in unique_student_ids:
        db.add(ParentMessageRecipient(message_id=msg.id, student_id=sid))

    db.commit()
    db.refresh(msg)

    return ParentMessageOut(
        id=msg.id,
        message_id=msg.id,
        school_id=msg.school_id,
        section_id=msg.section_id,
        subject=msg.subject,
        message=msg.message,
        student_ids=unique_student_ids,
        delivered_count=len(unique_student_ids),
        created_by=msg.created_by_user_id,
        created_at=msg.created_at,
    )


@router.get("/parent-messages", response_model=List[ParentMessageOut])
def list_parent_messages(
    school_id: int = Depends(get_valid_school_id),
    section_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher_or_principal),
):
    if section_id is not None:
        _ensure_section_in_school(db, school_id, section_id)

    q = db.query(ParentMessage).filter(ParentMessage.school_id == school_id)
    if section_id is not None:
        q = q.filter(ParentMessage.section_id == section_id)
    else:
        is_teacher = normalize_role(current_user.role) == "TEACHER"
        if is_teacher:
            # No section filter: return only the teacher's own history
            q = q.filter(ParentMessage.created_by_user_id == current_user.id)

    messages = q.order_by(ParentMessage.created_at.desc()).all()
    if not messages:
        return []

    message_ids = [m.id for m in messages]
    recipients = (
        db.query(ParentMessageRecipient)
        .filter(ParentMessageRecipient.message_id.in_(message_ids))
        .all()
    )
    recipients_by_msg: dict[int, list[int]] = {}
    for r in recipients:
        recipients_by_msg.setdefault(r.message_id, []).append(r.student_id)

    return [
        ParentMessageOut(
            id=m.id,
            message_id=m.id,
            school_id=m.school_id,
            section_id=m.section_id,
            subject=m.subject,
            message=m.message,
            student_ids=recipients_by_msg.get(m.id, []),
            delivered_count=len(recipients_by_msg.get(m.id, [])),
            created_by=m.created_by_user_id,
            created_at=m.created_at,
        )
        for m in messages
    ]
