# src/user_service/test_event_model_return_and_order.py

from datetime import datetime

from user_service.models.event import (
    EventSchemaCreate,
    EventSchemaReturn,
    EventQuery,
    EventRepository,
)
from shared.database import get_db


def test_event_schema_return_roundtrip():
    dt = datetime(2025, 10, 15, 12, 0, 0)
    ret = EventSchemaReturn(
        id=1,
        when=dt,
        source="frontend",
        type="page-view",
        payload={"path": "/"},
        user="u1",
    )
    assert ret.id == 1
    assert ret.payload["path"] == "/"


def test_event_query_orders_by_when_and_id():
    # normal DB session
    gen = get_db()
    db = next(gen)
    try:
        repo = EventRepository(db=db)
        base = datetime(2025, 10, 15, 12, 0, 0)

        import asyncio

        async def _run():
            # make 2 events with same time so we can check secondary order
            e1 = await repo.create(
                EventSchemaCreate(
                    when=base,
                    source="src",
                    type="t",
                    payload={},
                    user="u1",
                )
            )
            e2 = await repo.create(
                EventSchemaCreate(
                    when=base,
                    source="src",
                    type="t",
                    payload={},
                    user="u2",
                )
            )
            out = await repo.query(EventQuery(source="src", type="t"))
            # must be ordered by (when, id)
            assert [e.id for e in out] == sorted([e1.id, e2.id])

        asyncio.run(_run())
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
