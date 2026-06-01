from fastapi import APIRouter

from app.api.v1.routes import (
    management_dashboard,
    management_schools,
    principal_dashboard,
    schools,
)

router = APIRouter()
router.include_router(schools.router)
router.include_router(management_dashboard.router)
router.include_router(management_schools.router)
router.include_router(principal_dashboard.router)
