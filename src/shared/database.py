from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session  # noqa: F401
from sqlalchemy.pool import StaticPool

_engine = None
_SessionLocal = None


def _ensure_sqlite_schema(engine):
    # Import models AFTER engine is created to avoid circulars
    from user_service.models.user import Base  # Base includes all models via imports
    # Make sure the Event model module is imported so its table is registered on Base
    import user_service.models.event  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Yields a DB session.
    - If DATABASE_* envs (or DATABASE_URL) are present -> Postgres.
    - Otherwise -> shared in-memory SQLite, with tables created automatically.
    """
    global _engine, _SessionLocal

    url = os.environ.get("DATABASE_URL")
    if not url:
        if {"DATABASE_HOST", "DATABASE_DB", "DATABASE_USER", "DATABASE_PASSWORD"} <= set(os.environ.keys()):
            host = os.environ["DATABASE_HOST"]
            db   = os.environ["DATABASE_DB"]
            user = os.environ["DATABASE_USER"]
            pwd  = os.environ["DATABASE_PASSWORD"]
            port = os.environ.get("DATABASE_PORT", "5432")
            url  = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
        else:
            # Shared in-memory SQLite for tests
            url = "sqlite+pysqlite:///:memory:"

    if _engine is None:
        if url.startswith("sqlite"):
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,   # ensures everyone shares the same in-memory DB
            )
            _ensure_sqlite_schema(_engine)
        else:
            _engine = create_engine(url)

        _SessionLocal = sessionmaker(bind=_engine)

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
