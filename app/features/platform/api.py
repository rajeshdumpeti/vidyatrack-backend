from fastapi import APIRouter

from app.api.v1.routes import cms, health, notifications, school_onboarding

router = APIRouter()
router.include_router(health.router)
router.include_router(notifications.router)
router.include_router(school_onboarding.router)
router.include_router(cms.router)
