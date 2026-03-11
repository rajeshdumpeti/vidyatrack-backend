from fastapi import APIRouter

from app.api.v1.routes import auth, auth_debug

router = APIRouter()
router.include_router(auth.router)
router.include_router(auth_debug.router)
