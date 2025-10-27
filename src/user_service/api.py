import os
from datetime import datetime, date, timedelta
from fastapi import Query
from .models.event import (
    EventSchemaCreate, EventSchemaReturn, EventQuery,
    EventRepository, get_event_repository
)
from .analytics import build_sessions_for_day, summarize_day, average_reports
#from typing import List
from fastapi import FastAPI, Depends, Response, HTTPException # noqa: F401
from sqlalchemy.orm import Session # noqa: F401
from sqlalchemy.exc import IntegrityError
# from pydantic import TypeAdapter
import logging
from nicegui import ui
from admin import main # noqa: F401
from dotenv import load_dotenv
from .models.user import UserRepository, UserSchemaCreate, UserSchemaReturn, UserSchemaUpdate, get_user_repository, password_verification
from .models.rate_limiter import check_rate_limiter

logger = logging.getLogger('uvicorn.error')
app = FastAPI()
load_dotenv()

@app.post("/users/", status_code=201, dependencies=[Depends(check_rate_limiter)])
async def create_user(user: UserSchemaCreate, response: Response, user_repo: UserRepository = Depends(get_user_repository)):
    try:
        new_user = await user_repo.create_with_id(user.name, user.id, user.email, user.password, user.tier) #can use without id but then we got to change some tests, so leaving as is works for both functions and the local admin
        return {"user": UserSchemaReturn.from_db_model(new_user)}
    except IntegrityError:
        response.status_code = 409
        return {"detail": "Item already exists"}
    except AssertionError:
        response.status_code = 422
        return {"detail": "Empty fields not allowed"}

@app.post("/users/{id}", dependencies=[Depends(check_rate_limiter)])
async def delete_user(id: int, delete: UserSchemaUpdate, user_repo: UserRepository = Depends(get_user_repository)):
    
    if not delete.password: 
        raise HTTPException(status_code=401, detail="Password required for deletion")
    
    user = await user_repo.get_by_id(id)
    if not user: 
        raise HTTPException(status_code=404, detail="User not found")
    
    if not password_verification(delete.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password for deletion")

    await user_repo.delete_by_id(user.id)
    return {"message": f"User '{user.id}' deleted successfully."}

@app.get("/all_users/", dependencies=[Depends(check_rate_limiter)])
async def list_users(user_repo: UserRepository = Depends(get_user_repository)):

    user_models = await user_repo.get_all()
    users = []
    for model in user_models:
        users.append(UserSchemaReturn.from_db_model(model))
    return {'users': users}

@app.get("/users/{name}", dependencies=[Depends(check_rate_limiter)])
async def get_user(name: str, user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_name(name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": UserSchemaReturn.from_db_model(user)}

@app.get("/users_by_id/{id}", dependencies=[Depends(check_rate_limiter)])
async def get_user_by_id(id: int, user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": UserSchemaReturn.from_db_model(user)}

@app.put("/users/{id}", dependencies=[Depends(check_rate_limiter)])
async def update_user(id: int, updates: UserSchemaUpdate, user_repo: UserRepository = Depends(get_user_repository)):
    
    if not updates.password: 
        raise HTTPException(status_code=401, detail="Password required for update")
    
    user = await user_repo.get_by_id(id)
    if not user: 
        raise HTTPException(status_code=404, detail="User not found")
    
    if not password_verification(updates.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password for update")
    
    try:
        if updates.new_password:
            update_user = await user_repo.update_password(id, updates.new_password)
            return {"user": UserSchemaReturn.from_db_model(update_user)}
        
        update_user = await user_repo.update_user(id, name=updates.name, email=updates.email, tier=updates.tier)
        return {"user": UserSchemaReturn.from_db_model(update_user)} 
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    
def _auth_ttl_seconds() -> int:
    try:
        return int(os.getenv("AUTH_TTL_SECONDS", "900"))
    except Exception:
        return 900
    
@app.post("/v2/events/", status_code=201)
async def create_event(
    data: EventSchemaCreate,
    repo: EventRepository = Depends(get_event_repository),
):
    ev = await repo.create(data)
    return {"event": EventSchemaReturn.model_validate(ev.__dict__, from_attributes=True)}

@app.get("/v2/events/")
async def query_events(
    type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    user: str | None = Query(default=None),
    before: str | None = Query(default=None, description="YYYY-MM-DD HH:MM:SS"),
    after: str | None = Query(default=None, description="YYYY-MM-DD HH:MM:SS"),
    repo: EventRepository = Depends(get_event_repository),
):
    def parse(dt: str | None):
        return None if dt is None else datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")

    q = EventQuery(type=type, source=source, user=user, before=parse(before), after=parse(after))
    events = await repo.query(q)
    out = [
        EventSchemaReturn(id=e.id, when=e.when, source=e.source, type=e.type, payload=e.payload, user=e.user)
        for e in events
    ]
    return {"events": out}

@app.get("/v2/analytics")
async def analytics(
    on: str | None = Query(default=None, description="YYYY-MM-DD"),
    since: str | None = Query(default=None, description="YYYY-MM-DD"),
    repo: EventRepository = Depends(get_event_repository),
):
    ttl = _auth_ttl_seconds()

    def parse_day(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()

    if on and since:
        raise HTTPException(status_code=400, detail="Use either ?on= or ?since=, not both.")

    async def day_report(d: date) -> dict:
        start = datetime.combine(d, datetime.min.time()).replace(microsecond=0)
        end = datetime.combine(d, datetime.max.time()).replace(microsecond=0)
        q = EventQuery(after=start - timedelta(seconds=ttl), before=end)
        events = [e for e in await repo.query(q) if e.user is not None]
        stats = build_sessions_for_day(events, ttl, d)
        return summarize_day(stats)

    if since:
        sday = parse_day(since)
        if (datetime.now().date() - sday).days > 365:
            raise HTTPException(status_code=400, detail="since too far in the past")
        reports, cur, today = [], sday, datetime.now().date()
        while cur <= today:
            reports.append(await day_report(cur))
            cur += timedelta(days=1)
        return average_reports(reports)

    target = parse_day(on) if on else datetime.now().date()
    return await day_report(target)

ui.run_with(app,
            mount_path="/admin",
            favicon="👤",
            title="User Admin",
            storage_secret=os.getenv('STORAGE_SECRET'))
