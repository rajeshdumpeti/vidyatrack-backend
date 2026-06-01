from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
    ManagementSetupStepOut,
)
from app.core.roles import normalize_role
from app.db.models.class_ import Class
from app.db.models.class_subject import ClassSubject
from app.db.models.fee_structure import FeeStructure
from app.db.models.school import School
from app.db.models.school_academic_details import SchoolAcademicDetails
from app.db.models.school_contact import SchoolContact
from app.db.models.school_features import SchoolFeatures
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.subject import Subject
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.services.public_id import get_tenant_code_for_school, next_public_id


def _require_school_access(db: Session, *, school_id: int, current_user: User) -> School:
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail={"code": "SCHOOL_NOT_FOUND"})

    if normalize_role(current_user.role) == "SUPER_ADMIN":
        return school

    mapping = (
        db.query(UserSchool)
        .filter(
            UserSchool.school_id == school_id,
            UserSchool.user_id == current_user.id,
            UserSchool.is_active.is_(True),
        )
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=403, detail={"code": "NO_SCHOOL_ACCESS"})
    return school


def _build_status(db: Session, *, school: School) -> ManagementSetupStatusOut:
    school_id = school.id
    contact = (
        db.query(SchoolContact)
        .filter(SchoolContact.school_id == school_id)
        .first()
    )
    sections_count = (
        db.execute(
            select(func.count(Section.id)).where(
                Section.school_id == school_id,
                Section.is_active.is_(True),
            )
        ).scalar_one()
    )
    class_subject_count = (
        db.execute(
            select(func.count(ClassSubject.id)).where(
                ClassSubject.school_id == school_id,
                ClassSubject.is_active.is_(True),
            )
        ).scalar_one()
    )
    fee_plan_count = (
        db.execute(
            select(func.count(FeeStructure.id)).where(
                FeeStructure.school_id == school_id,
                FeeStructure.is_active.is_(True),
            )
        ).scalar_one()
    )
    principal_count = (
        db.execute(
            select(func.count(UserSchool.user_id)).where(
                UserSchool.school_id == school_id,
                UserSchool.role.ilike("PRINCIPAL"),
                UserSchool.is_active.is_(True),
            )
        ).scalar_one()
    )
    teacher_count = (
        db.execute(
            select(func.count(UserSchool.user_id)).where(
                UserSchool.school_id == school_id,
                UserSchool.role.ilike("TEACHER"),
                UserSchool.is_active.is_(True),
            )
        ).scalar_one()
    )
    student_count = (
        db.execute(select(func.count(Student.id)).where(Student.school_id == school_id)).scalar_one()
    )

    steps = [
        ManagementSetupStepOut(
            key="school_profile",
            label="School profile confirmed",
            completed=bool(
                contact
                and (
                    contact.street
                    or contact.city
                    or contact.state
                    or contact.pin_code
                    or contact.school_phone
                    or contact.school_email
                )
            ),
        ),
        ManagementSetupStepOut(
            key="sections",
            label="Sections created",
            completed=int(sections_count or 0) > 0,
            count=int(sections_count or 0),
        ),
        ManagementSetupStepOut(
            key="subjects",
            label="Subjects linked to grades",
            completed=int(class_subject_count or 0) > 0,
            count=int(class_subject_count or 0),
        ),
        ManagementSetupStepOut(
            key="fee_plans",
            label="Fee plans configured",
            completed=int(fee_plan_count or 0) > 0,
            count=int(fee_plan_count or 0),
        ),
        ManagementSetupStepOut(
            key="principal",
            label="Principal assigned",
            completed=int(principal_count or 0) > 0,
            count=int(principal_count or 0),
        ),
        ManagementSetupStepOut(
            key="teachers",
            label="Teachers onboarded",
            completed=int(teacher_count or 0) > 0,
            count=int(teacher_count or 0),
        ),
        ManagementSetupStepOut(
            key="students",
            label="Students enrolled",
            completed=int(student_count or 0) > 0,
            count=int(student_count or 0),
        ),
    ]
    completed_steps = sum(1 for step in steps if step.completed)
    total_steps = len(steps)
    completion_pct = int(round((completed_steps / max(total_steps, 1)) * 100))
    return ManagementSetupStatusOut(
        school_id=school_id,
        management_setup_complete=bool(school.management_setup_complete),
        management_setup_completed_at=school.management_setup_completed_at.isoformat()
        if school.management_setup_completed_at
        else None,
        completion_pct=completion_pct,
        completed_steps=completed_steps,
        total_steps=total_steps,
        steps=steps,
    )


def get_setup_status(db: Session, *, school_id: int, current_user: User) -> ManagementSetupStatusOut:
    school = _require_school_access(db, school_id=school_id, current_user=current_user)
    return _build_status(db, school=school)


def get_school_profile(
    db: Session, *, school_id: int, current_user: User
) -> ManagementSchoolProfileOut:
    school = _require_school_access(db, school_id=school_id, current_user=current_user)
    contact = (
        db.query(SchoolContact)
        .filter(SchoolContact.school_id == school.id)
        .first()
    )
    academic = (
        db.query(SchoolAcademicDetails)
        .filter(SchoolAcademicDetails.school_id == school.id)
        .first()
    )
    features = (
        db.query(SchoolFeatures)
        .filter(SchoolFeatures.school_id == school.id)
        .first()
    )
    return ManagementSchoolProfileOut(
        school_id=school.id,
        school_name=school.name,
        school_code=school.code,
        board=school.board,
        category=school.category,
        medium=school.medium,
        school_type=school.school_type,
        established_year=school.established_year,
        current_session=academic.current_session if academic else None,
        working_days_per_week=academic.working_days_per_week if academic else None,
        academic_start_month=academic.academic_start_month if academic else None,
        academic_end_month=academic.academic_end_month if academic else None,
        class_levels=academic.class_levels if academic and academic.class_levels else [],
        street=contact.street if contact else None,
        area=contact.area if contact else None,
        city=contact.city if contact else None,
        district=contact.district if contact else None,
        state=contact.state if contact else None,
        pin_code=contact.pin_code if contact else None,
        country=contact.country if contact else None,
        landmark=contact.landmark if contact else None,
        school_phone=contact.school_phone if contact else None,
        school_email=contact.school_email if contact else None,
        website=contact.website if contact else None,
        modules_enabled=features.modules_enabled if features and features.modules_enabled else [],
    )


def update_school_profile(
    db: Session,
    *,
    school_id: int,
    payload: ManagementSchoolProfileUpdateIn,
    current_user: User,
) -> ManagementSchoolProfileOut:
    school = _require_school_access(db, school_id=school_id, current_user=current_user)
    contact = db.query(SchoolContact).filter(SchoolContact.school_id == school.id).first()
    if not contact:
        contact = SchoolContact(school_id=school.id, created_by=current_user.id)
    academic = (
        db.query(SchoolAcademicDetails)
        .filter(SchoolAcademicDetails.school_id == school.id)
        .first()
    )
    if not academic:
        academic = SchoolAcademicDetails(school_id=school.id, created_by=current_user.id)

    school_email = (payload.school_email or "").strip().lower() or None
    if school_email:
        existing = (
            db.query(SchoolContact.id)
            .filter(
                func.lower(func.trim(SchoolContact.school_email)) == school_email,
                SchoolContact.school_id != school.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "CONFLICT", "conflicts": ["SCHOOL_EMAIL_ALREADY_EXISTS"]},
            )

    school.board = payload.board
    school.category = payload.category
    school.medium = payload.medium
    school.school_type = payload.school_type
    school.established_year = payload.established_year

    contact.street = payload.street
    contact.area = payload.area
    contact.city = payload.city
    contact.district = payload.district
    contact.state = payload.state
    contact.pin_code = payload.pin_code
    contact.country = payload.country or "India"
    contact.landmark = payload.landmark
    contact.school_phone = payload.school_phone
    contact.school_email = school_email
    contact.website = payload.website
    contact.updated_by = current_user.id

    academic.current_session = payload.current_session
    academic.working_days_per_week = payload.working_days_per_week
    academic.academic_start_month = payload.academic_start_month
    academic.academic_end_month = payload.academic_end_month
    academic.class_levels = payload.class_levels
    academic.lkg_available = "LKG" in payload.class_levels
    academic.ukg_available = "UKG" in payload.class_levels
    academic.pre_nursery_available = "Pre Nursery" in payload.class_levels
    academic.updated_by = current_user.id

    db.add(school)
    db.add(contact)
    db.add(academic)
    db.commit()
    return get_school_profile(db, school_id=school_id, current_user=current_user)


def complete_setup(db: Session, *, school_id: int, current_user: User) -> ManagementSetupCompleteOut:
    school = _require_school_access(db, school_id=school_id, current_user=current_user)
    status_snapshot = _build_status(db, school=school)
    incomplete = [step.label for step in status_snapshot.steps if not step.completed]
    if incomplete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SETUP_INCOMPLETE", "missing_steps": incomplete},
        )

    school.management_setup_complete = True
    school.management_setup_completed_at = datetime.now(timezone.utc)
    db.add(school)
    db.commit()
    db.refresh(school)
    return ManagementSetupCompleteOut(
        success=True,
        management_setup_complete=True,
        completed_at=school.management_setup_completed_at.isoformat(),
    )


def list_sections(db: Session, *, school_id: int, current_user: User) -> list[ManagementSectionGroupOut]:
    _require_school_access(db, school_id=school_id, current_user=current_user)
    rows = (
        db.query(Class, Section)
        .outerjoin(
            Section,
            (Section.class_id == Class.id)
            & (Section.school_id == school_id)
            & (Section.is_active.is_(True)),
        )
        .filter(Class.school_id == school_id)
        .order_by(Class.name.asc(), Section.name.asc())
        .all()
    )
    grouped: dict[int, ManagementSectionGroupOut] = {}
    for class_row, section_row in rows:
        group = grouped.setdefault(
            class_row.id,
            ManagementSectionGroupOut(
                class_id=class_row.id,
                class_name=class_row.name,
                sections=[],
            ),
        )
        if section_row:
            group.sections.append(
                ManagementSectionOut(
                    id=section_row.id,
                    public_id=section_row.public_id,
                    school_id=section_row.school_id,
                    class_id=section_row.class_id,
                    class_name=class_row.name,
                    name=section_row.name,
                    capacity=section_row.capacity,
                    room_number=section_row.room_number,
                    is_active=section_row.is_active,
                )
            )
    return list(grouped.values())


def create_section(
    db: Session,
    *,
    school_id: int,
    payload: ManagementSectionCreateIn,
    current_user: User,
) -> ManagementSectionOut:
    _require_school_access(db, school_id=school_id, current_user=current_user)
    class_row = (
        db.query(Class)
        .filter(Class.id == payload.class_id, Class.school_id == school_id)
        .first()
    )
    if not class_row:
        raise HTTPException(status_code=400, detail={"code": "INVALID_CLASS_ID"})

    existing = (
        db.query(Section)
        .filter(
            Section.school_id == school_id,
            Section.class_id == payload.class_id,
            func.lower(Section.name) == payload.name.strip().lower(),
        )
        .first()
    )
    if existing and existing.is_active:
        raise HTTPException(status_code=409, detail={"code": "SECTION_ALREADY_EXISTS"})
    if existing and not existing.is_active:
        existing.is_active = True
        existing.capacity = payload.capacity
        existing.room_number = payload.room_number
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return ManagementSectionOut(
            id=existing.id,
            public_id=existing.public_id,
            school_id=existing.school_id,
            class_id=existing.class_id,
            class_name=class_row.name,
            name=existing.name,
            capacity=existing.capacity,
            room_number=existing.room_number,
            is_active=existing.is_active,
        )

    row = Section(
        school_id=school_id,
        class_id=payload.class_id,
        name=payload.name.strip(),
        capacity=payload.capacity,
        room_number=payload.room_number.strip() if payload.room_number else None,
        is_active=True,
        public_id=next_public_id(
            db,
            tenant_code=get_tenant_code_for_school(db, school_id),
            entity="section",
        ),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ManagementSectionOut(
        id=row.id,
        public_id=row.public_id,
        school_id=row.school_id,
        class_id=row.class_id,
        class_name=class_row.name,
        name=row.name,
        capacity=row.capacity,
        room_number=row.room_number,
        is_active=row.is_active,
    )


def delete_section(db: Session, *, school_id: int, section_id: int, current_user: User) -> dict[str, bool]:
    _require_school_access(db, school_id=school_id, current_user=current_user)
    row = (
        db.query(Section)
        .filter(
            Section.id == section_id,
            Section.school_id == school_id,
            Section.is_active.is_(True),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail={"code": "SECTION_NOT_FOUND"})
    row.is_active = False
    db.add(row)
    db.commit()
    return {"success": True}


def list_class_subjects(
    db: Session,
    *,
    school_id: int,
    class_id: int,
    current_user: User,
) -> ManagementClassSubjectsResponse:
    _require_school_access(db, school_id=school_id, current_user=current_user)
    class_row = (
        db.query(Class)
        .filter(Class.id == class_id, Class.school_id == school_id)
        .first()
    )
    if not class_row:
        raise HTTPException(status_code=404, detail={"code": "CLASS_NOT_FOUND"})

    rows = (
        db.query(ClassSubject, Subject)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .filter(
            ClassSubject.school_id == school_id,
            ClassSubject.class_id == class_id,
            ClassSubject.is_active.is_(True),
        )
        .order_by(Subject.name.asc())
        .all()
    )
    subject_catalog = (
        db.query(Subject)
        .filter(Subject.school_id == school_id)
        .order_by(Subject.name.asc())
        .all()
    )
    return ManagementClassSubjectsResponse(
        class_id=class_row.id,
        class_name=class_row.name,
        subjects=[
            ManagementClassSubjectOut(
                id=mapping.id,
                public_id=mapping.public_id,
                class_id=mapping.class_id,
                class_name=class_row.name,
                subject_id=subject.id,
                subject_name=subject.name,
                subject_type=mapping.subject_type,
                max_marks=mapping.max_marks,
                passing_marks=mapping.passing_marks,
                is_active=mapping.is_active,
            )
            for mapping, subject in rows
        ],
        subject_catalog=[
            {"id": item.id, "name": item.name}
            for item in subject_catalog
        ],
    )


def create_class_subject(
    db: Session,
    *,
    school_id: int,
    payload: ManagementClassSubjectCreateIn,
    current_user: User,
) -> ManagementClassSubjectOut:
    _require_school_access(db, school_id=school_id, current_user=current_user)
    class_row = (
        db.query(Class)
        .filter(Class.id == payload.class_id, Class.school_id == school_id)
        .first()
    )
    if not class_row:
        raise HTTPException(status_code=404, detail={"code": "CLASS_NOT_FOUND"})

    subject = None
    if payload.subject_id:
        subject = (
            db.query(Subject)
            .filter(Subject.id == payload.subject_id, Subject.school_id == school_id)
            .first()
        )
    elif payload.name and payload.name.strip():
        subject = (
            db.query(Subject)
            .filter(
                Subject.school_id == school_id,
                func.lower(Subject.name) == payload.name.strip().lower(),
            )
            .first()
        )
        if not subject:
            subject = Subject(
                school_id=school_id,
                name=payload.name.strip(),
                public_id=next_public_id(
                    db,
                    tenant_code=get_tenant_code_for_school(db, school_id),
                    entity="subject",
                ),
            )
            db.add(subject)
            db.flush()
    if not subject:
        raise HTTPException(status_code=400, detail={"code": "SUBJECT_REQUIRED"})

    existing = (
        db.query(ClassSubject)
        .filter(
            ClassSubject.school_id == school_id,
            ClassSubject.class_id == payload.class_id,
            ClassSubject.subject_id == subject.id,
        )
        .first()
    )
    if existing and existing.is_active:
        raise HTTPException(status_code=409, detail={"code": "SUBJECT_ALREADY_LINKED"})
    if existing and not existing.is_active:
        existing.is_active = True
        existing.subject_type = payload.subject_type
        existing.max_marks = payload.max_marks
        existing.passing_marks = payload.passing_marks
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return ManagementClassSubjectOut(
            id=existing.id,
            public_id=existing.public_id,
            class_id=existing.class_id,
            class_name=class_row.name,
            subject_id=subject.id,
            subject_name=subject.name,
            subject_type=existing.subject_type,
            max_marks=existing.max_marks,
            passing_marks=existing.passing_marks,
            is_active=existing.is_active,
        )

    row = ClassSubject(
        school_id=school_id,
        class_id=payload.class_id,
        subject_id=subject.id,
        subject_type=payload.subject_type,
        max_marks=payload.max_marks,
        passing_marks=payload.passing_marks,
        is_active=True,
        public_id=next_public_id(
            db,
            tenant_code=get_tenant_code_for_school(db, school_id),
            entity="classsubject",
        ),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ManagementClassSubjectOut(
        id=row.id,
        public_id=row.public_id,
        class_id=row.class_id,
        class_name=class_row.name,
        subject_id=subject.id,
        subject_name=subject.name,
        subject_type=row.subject_type,
        max_marks=row.max_marks,
        passing_marks=row.passing_marks,
        is_active=row.is_active,
    )


def delete_class_subject(
    db: Session,
    *,
    school_id: int,
    class_subject_id: int,
    current_user: User,
) -> dict[str, bool]:
    _require_school_access(db, school_id=school_id, current_user=current_user)
    row = (
        db.query(ClassSubject)
        .filter(
            ClassSubject.id == class_subject_id,
            ClassSubject.school_id == school_id,
            ClassSubject.is_active.is_(True),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail={"code": "CLASS_SUBJECT_NOT_FOUND"})
    row.is_active = False
    db.add(row)
    db.commit()
    return {"success": True}
