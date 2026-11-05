"""
ManuMind AI - Database Engine and Session Management
Configured for Supabase PostgreSQL (Session Pooler) and SQLite local fallback.
"""

import os
import re
from typing import Generator, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import settings
from backend.app.utils.logging import logger


def get_normalized_database_url(raw_url: str | None = None) -> str:
    """
    Normalize DATABASE_URL for SQLAlchemy:
    - Normalizes legacy 'postgres://' to 'postgresql://'
    - Normalizes 'postgresql+psycopg://' to 'postgresql+psycopg2://' if psycopg v3
      is not installed but psycopg2 is available.
    """
    url = raw_url or settings.DATABASE_URL
    if not url:
        return f"sqlite:///{settings.BASE_PATH}/manumind.db"

    # Normalize protocol
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # Check driver compatibility for psycopg v3 vs psycopg2
    if url.startswith("postgresql+psycopg://"):
        try:
            import psycopg  # noqa: F401
        except ImportError:
            # Fall back to installed psycopg2 driver
            url = "postgresql+psycopg2://" + url[len("postgresql+psycopg://"):]

    # Ensure sslmode=require for Supabase pooler
    if "pooler.supabase.com" in url and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    return url


def build_engine(raw_url: str | None = None):
    """
    Construct SQLAlchemy engine with appropriate connection pooling,
    SSL options, and timeouts based on dialect.
    """
    normalized_url = get_normalized_database_url(raw_url)
    connect_args: Dict[str, Any] = {}
    engine_kwargs: Dict[str, Any] = {
        "pool_pre_ping": True,
        "echo": False
    }

    if normalized_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif "postgresql" in normalized_url:
        # PostgreSQL / Supabase Pooler optimizations
        connect_args["connect_timeout"] = 10
        engine_kwargs["pool_recycle"] = 300  # recycle connection every 5 min to avoid idle disconnects
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    engine_kwargs["connect_args"] = connect_args
    return create_engine(normalized_url, **engine_kwargs)


# Initialize global engine
engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to yield database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Create all registered database tables on the active database."""
    import backend.app.models.machine
    import backend.app.models.sensor_reading
    import backend.app.models.maintenance_history
    import backend.app.models.alert
    import backend.app.models.ticket

    active_engine = target_engine or engine
    Base.metadata.create_all(bind=active_engine)
