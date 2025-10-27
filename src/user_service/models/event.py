from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Generator

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, DateTime, Integer, String, Index, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from .user import Base
from shared.database import get_db


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    when = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    user = Column(String, nullable=True, index=True)

    __table_args__ = (
        Index("ix_events_when_user", "when", "user"),
        Index("ix_events_type_source_when", "type", "source", "when"),
    )


class EventSchemaCreate(BaseModel):
    when: datetime
    source: str
    type: str = Field(alias="type")
    payload: dict
    user: Optional[str] = None

    @field_validator("source")
    @classmethod
    def _source_not_empty(cls, v: str) -> str:
        assert v.strip(), "source must be non-empty"
        return v

    class Config:
        populate_by_name = True


class EventSchemaReturn(BaseModel):
    id: int
    when: datetime
    source: str
    type: str
    payload: dict
    user: Optional[str] = None


class EventQuery(BaseModel):
    type: Optional[str] = None
    source: Optional[str] = None
    user: Optional[str] = None
    after: Optional[datetime] = None
    before: Optional[datetime] = None


@dataclass
class EventRepository:
    db: Session

    async def create(self, data: EventSchemaCreate) -> Event:
        ev = Event(
            when=data.when, source=data.source, type=data.type,
            payload=data.payload, user=data.user
        )
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev

    async def query(self, q: EventQuery) -> List[Event]:
        stmt = self.db.query(Event)
        if q.type:
            stmt = stmt.filter(Event.type == q.type)
        if q.source:
            stmt = stmt.filter(Event.source == q.source)
        if q.user is not None:
            stmt = stmt.filter(Event.user == q.user)
        if q.after:
            stmt = stmt.filter(Event.when >= q.after)
        if q.before:
            stmt = stmt.filter(Event.when <= q.before)
        return list(stmt.order_by(Event.when.asc(), Event.id.asc()).all())


def get_event_repository() -> Generator[EventRepository, None, None]:
    """FastAPI dependency that yields an EventRepository and closes the DB session."""
    gen = get_db()          # this is the generator from your DB util
    db = next(gen)          # open a session
    try:
        yield EventRepository(db=db)
    finally:
        try:
            next(gen)       # let get_db() do its cleanup/close
        except StopIteration:
            pass
