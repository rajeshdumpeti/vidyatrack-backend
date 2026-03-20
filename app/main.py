import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.seed import seed_super_admin

logger = logging.getLogger(__name__)

setup_logging()


_CORS_BY_ENV: dict[str, list[str]] = {
    "dev": [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://dev.vidyatrack.in",
    ],
    "stage": [
        "https://stage.vidyatrack.in",
    ],
    "prod": [
        "https://vidyatrack.in",
        "https://www.vidyatrack.in",
    ],
    "test": [
        "http://localhost:5173",
    ],
}


def _parse_cors_origins(raw: str) -> list[str]:
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return _CORS_BY_ENV.get(settings.environment, _CORS_BY_ENV["dev"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_super_admin()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
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
