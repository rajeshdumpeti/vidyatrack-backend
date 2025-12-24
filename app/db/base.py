from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Central SQLAlchemy Declarative Base.

    Why this exists:
    - All ORM models must inherit from this Base
    - Alembic uses this to auto-detect schema changes
    - Keeps model metadata centralized and consistent
    """
    pass
