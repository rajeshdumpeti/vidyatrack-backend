from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.school import School
from app.db.models.user import User  # Import User model to create the admin
from app.db.models.user_school import UserSchool

router = APIRouter(prefix="/schools", tags=["schools"])


class SchoolCreate(BaseModel):
    name: str
    admin_phone: str


class SchoolOut(BaseModel):
    id: int
    name: str
    teacher_count: int = 0
    student_count: int = 0

    class Config:
        from_attributes = True


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


@router.post("", response_model=SchoolOut, status_code=201)
def create_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only you (SUPER_ADMIN) should be able to create new schools
    if current_user.role != "super_admin":
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
                role="management",
                is_active=True
            )
            db.add(admin_user)
            db.flush()  # Get the admin_user.id
        else:
            admin_user = existing_user

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
