"""Database connection, engine configuration, and session management."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Optional

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base


def get_database_url() -> str:
    """Retrieve database URL from environment with sensible defaults."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    # Assemble from POSTGRES_* environment variables if DATABASE_URL is not set
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "urban_intelligence")

    # Prefer psycopg (v3) or psycopg2 driver for postgresql
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def create_db_engine(url: Optional[str] = None, echo: bool = False, **kwargs: object) -> Engine:
    """Create a configured SQLAlchemy engine."""
    db_url = url or get_database_url()

    # If running SQLite in-memory, configure appropriate pool
    if db_url.startswith("sqlite"):
        return sa.create_engine(
            db_url,
            echo=echo,
            connect_args={"check_same_thread": False},
            **kwargs,
        )

    return sa.create_engine(
        db_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        **kwargs,
    )


# Default engine and sessionmaker
default_engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=default_engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session with automatic commit/rollback/close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def db_session(session_factory: Optional[sessionmaker[Session]] = None) -> Generator[Session, None, None]:
    """Context manager for standalone scripts or tasks."""
    factory = session_factory or SessionLocal
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Optional[Engine] = None) -> None:
    """Create all tables in the target database."""
    target_engine = engine or default_engine
    Base.metadata.create_all(bind=target_engine)
