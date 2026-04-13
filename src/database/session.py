"""
Database Session
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.database.models import Base

_DB_PATH = Path("inspection_ai.db")
_ENGINE = create_engine(f"sqlite:///{_DB_PATH}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)


def init_db() -> None:
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=_ENGINE)


@contextmanager
def get_session() -> Session:
    session = _SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
