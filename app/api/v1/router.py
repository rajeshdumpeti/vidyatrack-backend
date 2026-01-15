from fastapi import APIRouter

from app.api.v1.routes import health
from app.api.v1.routes import schools
from app.api.v1.routes import teachers
from app.api.v1.routes import auth
from app.api.v1.routes import auth_debug
from app.api.v1.routes import students
from app.api.v1.routes import classes
from app.api.v1.routes import sections
from app.api.v1.routes import attendance
from app.api.v1.routes import subjects
from app.api.v1.routes import marks
from app.api.v1.routes import notifications
from app.api.v1.routes import teacher_me
from app.api.v1.routes import student_notes
from app.api.v1.routes import teaching_assignments
from app.api.v1.routes import management_teachers
from app.api.v1.routes import teachers_me
api_router = APIRouter()


api_router.include_router(health.router)
api_router.include_router(schools.router)
api_router.include_router(teachers.router)
api_router.include_router(auth.router)
api_router.include_router(auth_debug.router)
api_router.include_router(students.router)
api_router.include_router(classes.router)
api_router.include_router(sections.router)
api_router.include_router(attendance.router)
api_router.include_router(subjects.router)
api_router.include_router(marks.router)
api_router.include_router(notifications.router)
api_router.include_router(teacher_me.router)
api_router.include_router(student_notes.router)
api_router.include_router(teaching_assignments.router)
api_router.include_router(management_teachers.router)
api_router.include_router(teachers_me.router)
