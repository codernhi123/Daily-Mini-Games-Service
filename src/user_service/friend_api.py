from typing import Literal, List, Optional
from fastapi import Depends, HTTPException, APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, delete, update
from sqlalchemy.orm import Session

from .models.friend import FriendRepository, FriendRequest, Friendship, get_friend_repository
from .models.user import User
from shared.database import get_db

router = APIRouter(prefix="/v2/users/", tags=["friends"])

class SendRequestBody(BaseModel):
    other: str # receiver

@router.get("/{user_name}/friend-requests/")
async def list_friend_requests(
    user_name: str,
    q: Literal["incoming", "outgoing"] = Query(...),
    repo: FriendRepository = Depends(get_friend_repository),
):
    if q == "incoming":
        rows = await repo.view_request_incoming(user_name)
    else:
        rows = await repo.view_request_outgoing(user_name)
    return [
        {
            "id": fr.id,
            "from": fr.requester,
            "to": fr.receiver,
            "status": fr.status,
            "created_at": fr.created_at,
        }
        for fr in rows
    ]

@router.post("/{user_name}/friend-requests/")
async def send_request(body: SendRequestBody, repo: FriendRepository = Depends(get_friend_repository)):
    try:
        await repo.send_request(body.requester, body.receiver)
        return {"ok": True, "message": "Request sent"}
    except ValueError as e:
        raise HTTPException(status_code = 400, detail = str(e))