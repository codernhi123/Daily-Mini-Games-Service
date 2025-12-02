# src/user_service/test_event_model_extra.py

from datetime import datetime, timedelta
import asyncio

import pytest

from user_service.models.event import (
    EventSchemaCreate,
    EventQuery,
    EventRepository,
    get_event_repository,
)
from shared.database import get_db


def _db_session():
    gen = get_db()
    db = next(gen)
    try:
        yield db
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_event_schema_create_alias_type_and_nonempty_source():
    data = EventSchemaCreate(
        when=datetime(2025, 10, 15, 12, 0, 0),
        source="frontend",
        type="page-view",
        payload={"path": "/"},
        user="u123",
    )
    assert data.type == "page-view"
    assert data.source == "frontend"


def test_event_repository_all_filters_together():
    for db in _db_session():
        repo = EventRepository(db=db)
        base = datetime(2025, 10, 15, 12, 0, 0)

        async def _run():
            e1 = await repo.create(
                EventSchemaCreate(
                    when=base,
                    source="srcA",
                    type="t1",
                    payload={},
                    user="u1",
                )
            )
            await repo.create(
                EventSchemaCreate(
                    when=base + timedelta(minutes=5),
                    source="srcA",
                    type="t1",
                    payload={},
                    user="u2",
                )
            )
            await repo.create(
                EventSchemaCreate(
                    when=base + timedelta(minutes=10),
                    source="srcB",
                    type="t2",
                    payload={},
                    user=None,
                )
            )

            q = EventQuery(
                type="t1",
                source="srcA",
                user="u1",
                after=base - timedelta(minutes=1),
                before=base + timedelta(minutes=6),
            )
            out = await repo.query(q)
            assert [e.id for e in out] == [e1.id]

        asyncio.run(_run())


def test_get_event_repository_yields_and_closes():
    gen = get_event_repository()
    repo = next(gen)
    assert hasattr(repo, "create")
    with pytest.raises(StopIteration):
        next(gen)
