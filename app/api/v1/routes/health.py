from fastapi import APIRouter

from app.api.v1.controllers import health as health_controller
from app.api.v1.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return health_controller.live()


@router.get("/health/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    return health_controller.ready()
