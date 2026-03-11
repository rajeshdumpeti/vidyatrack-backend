from fastapi import APIRouter

from app.api.v1.routes import (
    academic_setup,
    attendance,
    classes,
    marks,
    sections,
    subjects,
    teaching_assignments,
)

router = APIRouter()
router.include_router(classes.router)
router.include_router(sections.router)
router.include_router(subjects.router)
router.include_router(attendance.router)
router.include_router(marks.router)
router.include_router(teaching_assignments.router)
router.include_router(academic_setup.router)
