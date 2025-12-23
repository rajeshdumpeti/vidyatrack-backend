from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    """
    Liveness probe: confirms the process is running.
    No external dependencies.
    """
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    """
    Readiness probe: confirms the service is ready to serve traffic.
    For now, no DB check. We will add DB ping once SQLAlchemy is wired.
    """
    return HealthResponse(status="ok")
