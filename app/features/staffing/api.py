from fastapi import APIRouter

from app.api.v1.routes import (
    management_principal,
    management_portfolio,
    management_reports,
    management_settings,
    management_staff,
    management_teachers,
    teacher_me,
    teachers,
    teachers_me,
)

router = APIRouter()
router.include_router(teachers.router)
router.include_router(teacher_me.router)
router.include_router(teachers_me.router)
router.include_router(management_teachers.router)
router.include_router(management_principal.router)
router.include_router(management_portfolio.router)
router.include_router(management_reports.router)
router.include_router(management_settings.router)
router.include_router(management_staff.router)
