from fastapi import APIRouter

from app.features.academic.api import router as academic_router
from app.features.auth.api import router as auth_router
from app.features.communications.api import router as communications_router
from app.features.fees.api import router as fees_router
from app.features.platform.api import router as platform_router
from app.features.schools.api import router as schools_router
from app.features.staffing.api import router as staffing_router
from app.features.students.api import router as students_router

api_router = APIRouter()

api_router.include_router(platform_router)
api_router.include_router(auth_router)
api_router.include_router(schools_router)
api_router.include_router(students_router)
api_router.include_router(academic_router)
api_router.include_router(staffing_router)
api_router.include_router(communications_router)
api_router.include_router(fees_router)
