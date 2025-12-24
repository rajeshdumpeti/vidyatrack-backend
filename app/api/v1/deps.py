from typing import Generator

from app.db.session import SessionLocal


def get_db() -> Generator:
    """
    FastAPI dependency that provides a database session.

    Why this exists:
    - Ensures one DB session per request
    - Guarantees session is closed after request
    - Centralizes DB lifecycle management
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
