from fastapi import APIRouter

from app.api.v1.routes import fees

router = APIRouter()

router.include_router(fees.router)

