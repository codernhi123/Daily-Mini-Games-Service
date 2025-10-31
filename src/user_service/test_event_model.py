# src/user_service/test_event_model.py

from datetime import datetime, timedelta
import asyncio

import pytest
from pydantic import ValidationError

from user_service.models.event import (
    EventSchemaCreate,
    EventQuery,
    EventRepository,
    get_event_repository,
)
from shared.database import get_db


def test_event_schema_create_rejects_empty_source():
    # pydantic v2 wraps assertion → ValidationError
    with pytest.raises(ValidationError):
        EventSchemaCreate(
            when=datetime.utcnow(),
            source="   ",
            type="click",
            payload={},
            user=None,
        )


def _session():
    gen = get_db()
    db = next(gen)
    try:
        yield db
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_event_repo_create_and_query_all_branches():
    for db in _session():
        repo = EventRepository(db=db)

        now = datetime(2025, 10, 15, 10, 0, 0)

        async def _run():
            e1 = await repo.create(
                EventSchemaCreate(
                    when=now,
                    source="src1",
                    type="t1",
                    payload={"a": 1},
                    user="u1",
                )
            )
            e2 = await repo.create(
                EventSchemaCreate(
                    when=now + timedelta(minutes=5),
                    source="src2",
                    type="t1",
                    payload={"b": 2},
                    user=None,
                )
            )
            e3 = await repo.create(
                EventSchemaCreate(
                    when=now + timedelta(minutes=10),
                    source="src1",
                    type="t2",
                    payload={"c": 3},
                    user="u2",
                )
            )

            # filter by type
            out = await repo.query(EventQuery(type="t1"))
            assert [e.id for e in out] == [e1.id, e2.id]

            # filter by source
            out = await repo.query(EventQuery(source="src1"))
            assert [e.id for e in out] == [e1.id, e3.id]

            # filter by user (None vs not None)
            # In this repo, EventQuery(user=None) means "don't filter by user",
            # so we should get ALL events.
            out = await repo.query(EventQuery(user=None))
            ids = [e.id for e in out]
            assert set(ids) == {e1.id, e2.id, e3.id}

            # but an explicit user works:
            out = await repo.query(EventQuery(user="u1"))
            assert [e.id for e in out] == [e1.id]

            # time window
            out = await repo.query(
                EventQuery(
                    after=now + timedelta(minutes=1),
                    before=now + timedelta(minutes=9),
                )
            )
            assert [e.id for e in out] == [e2.id]

        asyncio.run(_run())


def test_get_event_repository_dependency_generator():
    gen = get_event_repository()
    repo = next(gen)
    assert hasattr(repo, "create")
    with pytest.raises(StopIteration):
        next(gen)
