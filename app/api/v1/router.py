from fastapi import APIRouter

from app.api.v1.routes import health
from app.api.v1.routes import schools


api_router = APIRouter()


api_router.include_router(health.router)
api_router.include_router(schools.router)
