from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session  # noqa: F401
from sqlalchemy.pool import StaticPool

_engine = None
_SessionLocal = None


def _resolve_database_url() -> str:
    """Support DATABASE_URL, DATABASE_* or POSTGRES_*; else use shared in-memory SQLite."""
    
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    # Prefer DATABASE_*
    if {"DATABASE_HOST", "DATABASE_DB", "DATABASE_USER", "DATABASE_PASSWORD"}.issubset(os.environ):
        host = os.environ["DATABASE_HOST"]
        db   = os.environ["DATABASE_DB"]
        user = os.environ["DATABASE_USER"]
        pwd  = os.environ["DATABASE_PASSWORD"]
        port = os.environ.get("DATABASE_PORT", "5432")
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"

    # Also accept POSTGRES_*
    if {"POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD"}.issubset(os.environ):
        host = os.environ["POSTGRES_HOST"]
        user = os.environ["POSTGRES_USER"]
        pwd  = os.environ["POSTGRES_PASSWORD"]
        db   = os.environ.get("POSTGRES_DB", user)
        port = os.environ.get("POSTGRES_PORT", "5432")
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"

    # Fallback for tests
    return "sqlite+pysqlite:///:memory:"


def _ensure_sqlite_schema(engine):
    # Import models AFTER engine is created to avoid circulars
    from user_service.models.user import Base  # Base includes all models via imports
    # Make sure the Event model module is imported so its table is registered on Base
    import user_service.models.event  # noqa: F401
    from user_service.models.user_v1 import Base_v1 
    import user_service.models.game
    
    Base.metadata.create_all(bind=engine)
    Base_v1.metadata.create_all(bind=engine)


def get_db():
    """
    Yields a DB session.
    - If DATABASE_* / POSTGRES_* (or DATABASE_URL) are present -> Postgres.
    - Otherwise -> shared in-memory SQLite, with tables created automatically.
    """
    global _engine, _SessionLocal

    # Lazy, idempotent init
    if _SessionLocal is None:
        url = _resolve_database_url()

        if _engine is None:
            if url.startswith("sqlite"):
                _engine = create_engine(
                    url,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,   # share in-memory DB across sessions
                )
                _ensure_sqlite_schema(_engine)
            else:
                _engine = create_engine(url)

        _SessionLocal = sessionmaker(
            bind=_engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
