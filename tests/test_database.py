# src/user_service/test_database.py
import pytest
import os
from contextlib import contextmanager

from shared import database
from sqlalchemy import text


@contextmanager
def _env(**vals):
    old = {}
    for k, v in vals.items():
        old[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_resolve_uses_database_url_first():
    with _env(
        DATABASE_URL="postgresql+psycopg2://u:p@h:5432/dbname",
        DATABASE_HOST=None,
        POSTGRES_HOST=None,
    ):
        url = database._resolve_database_url()
        assert url == "postgresql+psycopg2://u:p@h:5432/dbname"


def test_resolve_uses_database_star_if_present():
    with _env(
        DATABASE_URL=None,
        DATABASE_HOST="dbhost",
        DATABASE_DB="maindb",
        DATABASE_USER="user1",
        DATABASE_PASSWORD="pw1",
        DATABASE_PORT="5433",
        POSTGRES_HOST=None,
    ):
        url = database._resolve_database_url()
        assert url == "postgresql+psycopg2://user1:pw1@dbhost:5433/maindb"


def test_resolve_uses_postgres_star_if_present():
    with _env(
        DATABASE_URL=None,
        DATABASE_HOST=None,
        POSTGRES_HOST="pg",
        POSTGRES_USER="ali",
        POSTGRES_PASSWORD="secret",
        POSTGRES_DB="ali_db",
        POSTGRES_PORT="5555",
    ):
        url = database._resolve_database_url()
        assert url == "postgresql+psycopg2://ali:secret@pg:5555/ali_db"


def test_resolve_falls_back_to_sqlite_memory():
    with _env(
        DATABASE_URL=None,
        DATABASE_HOST=None,
        POSTGRES_HOST=None,
    ):
        url = database._resolve_database_url()
        assert url == "sqlite+pysqlite:///:memory:"


def test_get_db_yields_session_and_closes():
    with _env(
        DATABASE_URL=None,
        DATABASE_HOST=None,
        POSTGRES_HOST=None,
    ):
        gen = database.get_db()
        db = next(gen)
        result = db.execute(text("SELECT 1"))
        assert list(result)[0][0] == 1
        with pytest.raises(StopIteration):
            next(gen)



@contextmanager
def _env(**vals):
    old = {}
    for k, v in vals.items():
        old[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_get_db_sqlite_path_is_idempotent():
    with _env(
        DATABASE_URL=None,
        DATABASE_HOST=None,
        POSTGRES_HOST=None,
    ):
        gen1 = database.get_db()
        db1 = next(gen1)
        res1 = db1.execute(text("SELECT 1")).scalar()
        assert res1 == 1
        with pytest.raises(StopIteration):
            next(gen1)

        gen2 = database.get_db()
        db2 = next(gen2)
        res2 = db2.execute(text("SELECT 1")).scalar()
        assert res2 == 1
        with pytest.raises(StopIteration):
            next(gen2)

def test_get_db_postgres_like_url_creates_engine():
    # we don't actually connect to real postgres in docker test env,
    # we just want to force the "non-sqlite" branch in get_db().
    fake_url = "postgresql+psycopg2://user:pw@localhost:5432/somedb"
    with _env(DATABASE_URL=fake_url):
        gen = database.get_db()
        db = next(gen)
        # we just want to know we got a Session object with 'bind' set
        assert db.bind is not None
        # close
        try:
            next(gen)
        except StopIteration:
            pass
