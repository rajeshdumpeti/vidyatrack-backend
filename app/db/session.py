from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _build_database_url() -> str:
    """
    Build PostgreSQL DB URL from environment-backed settings.
    Prefer DATABASE_URL for cloud deploys; fallback to DB_* vars for local dev.
    """
    if settings.database_url:
        return settings.database_url

    return (
        f"postgresql+psycopg://{settings.db_user}:"
        f"{settings.db_password}@{settings.db_host}:"
        f"{settings.db_port}/{settings.db_name}"
    )


engine = create_engine(
    _build_database_url(),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
