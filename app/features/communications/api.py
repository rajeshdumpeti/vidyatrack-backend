from fastapi import APIRouter

from app.api.v1.routes import communications

router = APIRouter()
router.include_router(communications.router)
