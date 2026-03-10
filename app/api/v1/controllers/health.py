from app.api.v1.schemas.health import HealthResponse


def live() -> HealthResponse:
    """
    Liveness probe: confirms the process is running.
    No external dependencies.
    """
    return HealthResponse(status="ok")


def ready() -> HealthResponse:
    """
    Readiness probe: confirms the service is ready to serve traffic.
    For now, no DB check. We will add DB ping once SQLAlchemy is wired.
    """
    return HealthResponse(status="ok")
