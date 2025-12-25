from fastapi import APIRouter

from app.api.v1.routes import health
from app.api.v1.routes import schools
from app.api.v1.routes import teachers
from app.api.v1.routes import auth
from app.api.v1.routes import auth_debug
from app.api.v1.routes import students


api_router = APIRouter()


api_router.include_router(health.router)
api_router.include_router(schools.router)
api_router.include_router(teachers.router)
api_router.include_router(auth.router)
api_router.include_router(auth_debug.router)
api_router.include_router(students.router)
