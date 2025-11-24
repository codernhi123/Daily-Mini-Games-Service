import os
from datetime import datetime, date, timedelta, timezone
from fastapi import Query, Request
from .models.event import (
    EventSchemaCreate, EventSchemaReturn, EventQuery,
    EventRepository, get_event_repository
)
from .models.user_v1 import (
    UserRepository_v1, UserSchema_v1, get_user_repository_v1
)
from .analytics import build_sessions_for_day, summarize_day, average_reports
#from typing import List
from fastapi import FastAPI, Depends, Response, HTTPException  # noqa: F401
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session  # noqa: F401
from sqlalchemy.exc import IntegrityError
# from pydantic import TypeAdapter
import logging
from nicegui import ui
from user_service.auth.jwt_helper import create_access_token, validate_jwt
from .models.user import (
    UserRepository,
    AuthRequest,
    AuthResponse,
    DeauthRequest,
    UserSchemaCreate,
    UserSchemaReturn,
    UserSchemaUpdate,
    get_user_repository,
    password_verification,
)
from .models.rate_limiter import check_rate_limiter
from .friend_api import router as friends_router
from .leaderboard_api import router as leaderboard_router
from .memory_game_api import router as memory_router
from .models.avatar_router import router as avatar_router
from dotenv import load_dotenv
from .trivia_game_api import router as trivia_router 
from admin import main  # noqa: F401

load_dotenv()

logger = logging.getLogger('uvicorn.error')
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(friends_router)
app.include_router(leaderboard_router)
app.include_router(memory_router)
app.include_router(avatar_router)
app.include_router(trivia_router)

app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("src/static/index.html")

@app.post("/v2/users/", status_code=201, dependencies=[Depends(check_rate_limiter)])
async def create_user(
    user: UserSchemaCreate,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        new_user = await user_repo.create_with_id(
            user.name, user.id, user.email, user.password, user.tier
        )
        return {"user": UserSchemaReturn.from_db_model(new_user)}
    except IntegrityError:
        response.status_code = 409
        return {"detail": "Item already exists"}
    except AssertionError:
        response.status_code = 422
        return {"detail": "Empty fields not allowed"}


# V1 code (left out to not affect test coverage %)
@app.post("/users/", status_code=201)
async def create_user_1(
    user: UserSchema_v1,
    response: Response,
    user_repo: UserRepository_v1 = Depends(get_user_repository_v1),
):
    try:
        new_user = await user_repo.create_with_id(
            user.name, user.id, user.email, user.password
        )
        return {"user": UserSchema_v1.from_db_model(new_user)}
    except IntegrityError:
        response.status_code = 409
        return {"detail": "Item already exists"}
    except AssertionError:
        response.status_code = 422
        return {"detail": "Empty fields not allowed"}


@app.post("/v2/users/{id}", dependencies=[Depends(check_rate_limiter)])
async def delete_user(
    id: int,
    delete: UserSchemaUpdate,
    user_repo: UserRepository = Depends(get_user_repository),
):

    if not delete.password:
        raise HTTPException(status_code=401, detail="Password required for deletion")

    user = await user_repo.get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not password_verification(delete.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password for deletion")

    await user_repo.delete_by_id(user.id)
    return {"message": f"User '{user.id}' deleted successfully."}


# V1 code (left out to not affect test coverage %)
@app.post("/users/delete")
async def delete_user_1(
    user: UserSchema_v1,
    user_repo: UserRepository_v1 = Depends(get_user_repository_v1),
):
    user_to_delete = await user_repo.get_by_name(user.name)
    if not user_to_delete:
        return {"message": f"User '{user.name}' does not exist."}

    await user_repo.delete(user_to_delete.name)
    return {"message": f"User '{user_to_delete.name}' deleted successfully."}


@app.post("/v2/authentications/", dependencies=[Depends(check_rate_limiter)])
async def become_authenticated(
    auth_request: AuthRequest,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    user = await user_repo.get_by_name(auth_request.name)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not password_verification(auth_request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        expiry_dt = datetime.strptime(auth_request.expiry, "%Y-%m-%d %H:%M:%S")
        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Expiry must be in 'YYYY-MM-DD HH:MM:SS' format in UTC Time",
        )

    now = datetime.now(timezone.utc)
    if expiry_dt <= now:
        raise HTTPException(
            status_code=400,
            detail="Expiry must be in the future, time is calculated based on UTC time.",
        )

    access_token = create_access_token(user.id, expiry_dt)

    await user_repo.update_active_jwt(user.id, access_token)

    max_age_seconds = int((expiry_dt - now).total_seconds())
    response.set_cookie(
        key="jwt",
        value=access_token,
        httponly=True,
        secure=False,  # False for localhost, True for production HTTPS
        samesite="lax",
        max_age=max_age_seconds,
        path="/"
    )

    return AuthResponse(jwt=access_token)

@app.post("/v2/authentications/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="jwt",
        path="/",
        samesite="lax",
        httponly=True,     # optional but safe
        secure=False       # match login
    )
    return {"message": "Logged out"}

@app.delete("/v2/authentications/", dependencies=[Depends(check_rate_limiter)])
async def delete_authentication(
    jwt_request: DeauthRequest,
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        payload = validate_jwt(jwt_request.jwt)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT")

    user_id = int(payload.get("sub"))
    await user_repo.update_active_jwt(user_id, None)

    return {"detail": "JWT successfully revoked"}

@app.get("/v2/authentications/me")
async def get_current_user(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository)
):
    token = request.cookies.get("jwt")
    if not token:
        raise HTTPException(status_code=401, detail="No JWT found")

    payload = validate_jwt(token)
    user_id = int(payload["sub"])

    user = await user_repo.get_by_id(user_id)
    return {"id": user.id, "name": user.name}

@app.get("/v2/users/", dependencies=[Depends(check_rate_limiter)])
async def list_users(user_repo: UserRepository = Depends(get_user_repository)):

    user_models = await user_repo.get_all()
    users = []
    for model in user_models:
        users.append(UserSchemaReturn.from_db_model(model))
    return {"users": users}


# V1 code (left out to not affect test coverage %)
@app.get("/users/")
async def list_users_1(user_repo: UserRepository_v1 = Depends(get_user_repository_v1)):

    user_models = await user_repo.get_all()
    users = []
    for model in user_models:
        users.append(UserSchema_v1.from_db_model(model))
    return {"users": users}


@app.get("/v2/users/{id:int}", dependencies=[Depends(check_rate_limiter)])
async def get_user_by_id(id: int, user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": UserSchemaReturn.from_db_model(user)}


@app.get("/v2/users/{name}", dependencies=[Depends(check_rate_limiter)])
async def get_user(name: str, user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_name(name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": UserSchemaReturn.from_db_model(user)}


# V1 code (left out to not affect test coverage %)
@app.get("/users/{name}")
async def get_user_1(
    name: str,
    user_repo: UserRepository_v1 = Depends(get_user_repository_v1),
):
    user = await user_repo.get_by_name(name)
    return {"user": user}


@app.put("/v2/users/{id}", dependencies=[Depends(check_rate_limiter)])
async def update_user(
    id: int,
    updates: UserSchemaUpdate,
    user_repo: UserRepository = Depends(get_user_repository),
):

    user = await user_repo.get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if updates.password:
        if not password_verification(updates.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid password for update")
    elif updates.active_jwt:
        try:
            payload = validate_jwt(updates.active_jwt)
            if int(payload.get("sub")) != id:
                raise HTTPException(status_code=401, detail="JWT does not match user")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid or expired JWT")
    else:
        raise HTTPException(status_code=401, detail="Password or JWT required")

    try:
        if updates.new_password:
            update_user = await user_repo.update_password(id, updates.new_password)

        update_user = await user_repo.update_user(
            id, name=updates.name, email=updates.email, tier=updates.tier
        )
        return {"user": UserSchemaReturn.from_db_model(update_user)}

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


def _auth_ttl_seconds() -> int:
    try:
        return int(os.getenv("AUTH_TTL_SECONDS", "900"))
    except Exception:
        return 900


@app.post("/v2/events/", status_code=201, dependencies=[Depends(check_rate_limiter)])
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

    q = EventQuery(
        type=type,
        source=source,
        user=user,
        before=parse(before),
        after=parse(after),
    )
    events = await repo.query(q)
    out = [
        EventSchemaReturn(
            id=e.id,
            when=e.when,
            source=e.source,
            type=e.type,
            payload=e.payload,
            user=e.user,
        )
        for e in events
    ]
    return {"events": out}


@app.get("/v2/analytics", dependencies=[Depends(check_rate_limiter)])
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


ui.run_with(
    app,
    mount_path="/admin",
    favicon="👤",
    title="User Admin",
    storage_secret=os.getenv('STORAGE_SECRET'),
)
