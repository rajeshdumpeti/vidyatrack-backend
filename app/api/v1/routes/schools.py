from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user, require_super_admin
from app.db.models.school import School
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.user import User  # Import User model to create the admin
from app.db.models.user_school import UserSchool
from app.core.roles import normalize_role

router = APIRouter(prefix="/schools", tags=["schools"])


class SchoolCreate(BaseModel):
    name: str
    admin_phone: str
    admin_email: str | None = None


class SchoolOut(BaseModel):
    id: int
    name: str
    code: str | None = None
    board: str | None = None
    category: str | None = None
    medium: str | None = None
    school_type: str | None = None
    established_year: int | None = None
    affiliation_number: str | None = None
    udise_code: str | None = None
    status: str
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    teacher_count: int = 0
    student_count: int = 0

    class Config:
        from_attributes = True


class SchoolDashboardOut(BaseModel):
    school_id: int
    teacher_count: int
    student_count: int
    staff_count: int
    total_registered: int


class SchoolTeacherListItem(BaseModel):
    id: int
    school_id: int
    name: str
    email: str | None = None
    phone: str | None = None
    status: str = "active"


class SchoolStudentListItem(BaseModel):
    id: int
    school_id: int
    name: str
    parent_name: str | None = None
    parent_phone: str | None = None
    status: str = "active"


class SchoolStaffListItem(BaseModel):
    user_id: int
    school_id: int
    role: str
    name: str
    email: str | None = None
    phone: str | None = None
    status: str = "active"


def _get_school_or_404(db: Session, school_id: int) -> School:
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="school_not_found")
    return school


@router.get("", response_model=List[SchoolOut])
def list_schools(
    db: Session = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
):
    # This query calculates counts for Teachers and Students per school
    # It filters users by role and groups them by school_id
    schools = db.query(School).order_by(School.id.asc()).all()

    for school in schools:
        # Count teachers linked to this school via the mapping table
        school.teacher_count = db.query(UserSchool).filter(
            UserSchool.school_id == school.id,
            UserSchool.role == "teacher"
        ).count()

        # Count students linked to this school via the mapping table
        school.student_count = db.query(UserSchool).filter(
            UserSchool.school_id == school.id,
            UserSchool.role == "student"
        ).count()

    return schools


@router.get("/{school_id}/dashboard", response_model=SchoolDashboardOut)
def get_school_dashboard(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    _get_school_or_404(db, school_id)

    teacher_count = (
        db.query(func.count(Teacher.id))
        .filter(Teacher.school_id == school_id)
        .scalar()
        or 0
    )
    student_count = (
        db.query(func.count(Student.id))
        .filter(Student.school_id == school_id)
        .scalar()
        or 0
    )
    staff_count = (
        db.query(func.count(UserSchool.id))
        .filter(
            UserSchool.school_id == school_id,
            func.lower(UserSchool.role).notin_(["teacher", "student"]),
        )
        .scalar()
        or 0
    )

    return SchoolDashboardOut(
        school_id=school_id,
        teacher_count=teacher_count,
        student_count=student_count,
        staff_count=staff_count,
        total_registered=teacher_count + student_count + staff_count,
    )


@router.get("/{school_id}/teachers", response_model=List[SchoolTeacherListItem])
def get_school_teachers(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    _get_school_or_404(db, school_id)

    rows = (
        db.query(Teacher, User)
        .outerjoin(User, Teacher.user_id == User.id)
        .filter(Teacher.school_id == school_id)
        .order_by(Teacher.id.asc())
        .all()
    )

    return [
        SchoolTeacherListItem(
            id=teacher.id,
            school_id=teacher.school_id,
            name=teacher.name,
            email=teacher.email or (user.email if user else None),
            phone=(user.phone if user else None),
            status="active" if (not user or user.is_active) else "inactive",
        )
        for teacher, user in rows
    ]


@router.get("/{school_id}/students", response_model=List[SchoolStudentListItem])
def get_school_students(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    _get_school_or_404(db, school_id)

    students = (
        db.query(Student)
        .filter(Student.school_id == school_id)
        .order_by(Student.id.asc())
        .all()
    )

    return [
        SchoolStudentListItem(
            id=student.id,
            school_id=student.school_id,
            name=student.name,
            parent_name=student.parent_name,
            parent_phone=student.parent_phone,
            status="active",
        )
        for student in students
    ]


@router.get("/{school_id}/staff", response_model=List[SchoolStaffListItem])
def get_school_staff(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    _get_school_or_404(db, school_id)

    rows = (
        db.query(UserSchool, User)
        .join(User, UserSchool.user_id == User.id)
        .filter(
            UserSchool.school_id == school_id,
            func.lower(UserSchool.role).notin_(["teacher", "student"]),
        )
        .order_by(UserSchool.id.asc())
        .all()
    )

    return [
        SchoolStaffListItem(
            user_id=user.id,
            school_id=link.school_id,
            role=link.role,
            name=(user.email or user.phone or f"User {user.id}"),
            email=user.email,
            phone=user.phone,
            status="active" if user.is_active else "inactive",
        )
        for link, user in rows
    ]


@router.post("", response_model=SchoolOut, status_code=201)
def create_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only you (super_admin) should be able to create new schools
    if normalize_role(current_user.role) != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can onboard new schools",
        )

    try:
        # 1. Create the School
        new_school = School(name=payload.name)
        db.add(new_school)
        db.flush()  # This gets us the new_school.id without committing yet

        # 2. Create the Management Admin for this school
      # 1. Check if the user already exists
        existing_user = db.query(User).filter(
            User.phone == payload.admin_phone).first()

        if not existing_user:
            # Create a new user if they don't exist
            admin_user = User(
                phone=payload.admin_phone,
                email=payload.admin_email,
                role="management",
                is_active=True
            )
            db.add(admin_user)
            db.flush()  # Get the admin_user.id
        else:
            admin_user = existing_user
            if payload.admin_email and not admin_user.email:
                admin_user.email = payload.admin_email
                db.add(admin_user)

        # 2. Link this user to the school in the mapping table
        # This allows one phone number to access multiple schools
        # Ensure this import is available
        from app.db.models.user_school import UserSchool

        mapping = UserSchool(
            user_id=admin_user.id,
            school_id=new_school.id,
            role="management"
        )
        db.add(mapping)

        # 3. Commit both together
        db.commit()
        db.refresh(new_school)
        return new_school

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to onboard school: {str(e)}"
        )
