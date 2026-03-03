from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
import time
import logging
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

setup_logging()


def _parse_cors_origins(raw: str) -> list[str]:
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )
    return response

app.include_router(api_router, prefix="/api/v1")
