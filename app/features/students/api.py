from fastapi import APIRouter

from app.api.v1.routes import student_notes, students

router = APIRouter()
router.include_router(students.router)
router.include_router(student_notes.router)
