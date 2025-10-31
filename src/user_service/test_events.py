from datetime import datetime
from fastapi.testclient import TestClient

from user_service.api import app
from user_service.models.event import get_event_repository


# --- simple in-memory repo that mimics your EventRepository ---

class _MemEvent:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FakeEventRepo:
    def __init__(self):
        self._events = []
        self._next_id = 1

    async def create(self, data):
        ev = _MemEvent(
            id=self._next_id,
            when=data.when,
            source=data.source,
            type=data.type,
            payload=data.payload,
            user=data.user,
        )
        self._next_id += 1
        self._events.append(ev)
        return ev

    async def query(self, q):
        out = list(self._events)
        if q.type:
            out = [e for e in out if e.type == q.type]
        if q.source:
            out = [e for e in out if e.source == q.source]
        if q.user is not None:
            out = [e for e in out if e.user == q.user]
        if q.after:
            out = [e for e in out if e.when >= q.after]
        if q.before:
            out = [e for e in out if e.when <= q.before]
        return sorted(out, key=lambda e: (e.when, e.id))


def _override_dep(repo: FakeEventRepo):
    async def _dep():
        # yield like the real dependency
        try:
            yield repo
        finally:
            pass
    return _dep


def _client_with_repo():
    repo = FakeEventRepo()
    app.dependency_overrides[get_event_repository] = _override_dep(repo)
    client = TestClient(app)
    client._repo = repo  # handy handle if a test needs direct access
    return client


# def test_create_event_returns_201_and_payload():
#     client = _client_with_repo()
#     try:
#         body = {
#             "when": "2025-10-15 13:32:22",
#             "source": "http://localhost/blog/some-post",
#             "type": "text-highlight",
#             "payload": {"content": "hi"},
#             "user": "u1",
#         }
#         r = client.post("/v2/events/", json=body)
#         assert r.status_code == 201, r.text
#         ev = r.json()["event"]
#         assert ev["id"] == 1
#         assert ev["type"] == "text-highlight"
#         assert ev["source"] == "http://localhost/blog/some-post"
#         assert ev["payload"] == {"content": "hi"}
#         assert ev["user"] == "u1"
#         # API returns ISO 8601; just make sure it parses
#         datetime.fromisoformat(ev["when"].replace("Z", "+00:00"))
#     finally:
#         app.dependency_overrides.clear()
#         client.close()

