from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


_engine = None
_SessionLocal = None


def init_engine(database_url: str) -> None:
    global _engine, _SessionLocal
    _engine = create_engine(database_url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_engine():
    if _engine is None:
        raise RuntimeError("Database engine is not initialized")
    return _engine


def get_sessionmaker():
    if _SessionLocal is None:
        raise RuntimeError("Database sessionmaker is not initialized")
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
