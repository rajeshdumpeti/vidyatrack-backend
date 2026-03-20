from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine: Engine = create_engine(
    settings.resolved_database_url,
    **settings.sqlalchemy_engine_options,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    class_=Session,
    bind=engine,
)
