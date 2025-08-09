"""Database setup for PFTL using SQLAlchemy 2.0 style.

Provides engine, session factory, and Base, plus a FastAPI dependency to get a session.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from .core.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite:")


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite(settings.database_url) else {},
)

SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))


def get_db() -> Generator:
    """FastAPI dependency that yields a SQLAlchemy session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator:
    """Context manager for ad-hoc DB session usage outside request lifecycle."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
