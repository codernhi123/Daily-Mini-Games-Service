from typing import Literal
from fastapi import Depends, HTTPException, APIRouter, Query
from pydantic import BaseModel
from .models.rate_limiter import check_rate_limiter
from user_service.auth.jwt_helper import validate_jwt

from .models.friend import FriendRepository, get_friend_repository
from .models.user import UserRepository, get_user_repository
#from shared.database import get_db

router = APIRouter(prefix="/v2/users", tags=["friends"])

class SendRequestBody(BaseModel):
    other: int

async def require_auth_user(
    user_id: int,  # FastAPI injects the path param
    token: str,
    user_repo: UserRepository = Depends(get_user_repository),
) -> int:
    #Extract token from Authorization header
    if token is None:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    #Validate token
    try:
        payload = validate_jwt(token)  # raises ValueError on invalid/expired
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT")

    sub = payload.get("sub")
    try:
        sub_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Malformed JWT subject")

    #Token must belong to the same user as the path param
    if sub_id != user_id:
        raise HTTPException(status_code=401, detail="JWT does not match requested user")

    #Must match the user’s active_jwt in DB
    user = await user_repo.get_by_id(sub_id)
    if not user or user.active_jwt != token:
        raise HTTPException(status_code=401, detail="JWT is not active for this user")

    return sub_id

@router.get("/{user_id}/friend-requests/", status_code=200, dependencies=[Depends(check_rate_limiter)]) #Get unanswered requests made to/by a user
async def list_friend_requests(
    user_id: int,
    q: Literal["incoming", "outgoing"] = Query(...),
    repo: FriendRepository = Depends(get_friend_repository), 
):
    if q == "incoming":
        rows = await repo.view_request_incoming(user_id)
    else:
        rows = await repo.view_request_outgoing(user_id)
    return [
        {
            "from": fr.requester_id,
            "to": fr.receiver_id,
            "sent_timestamp": fr.created_at,
        }
        for fr in rows
    ]

@router.post("/{user_id}/friend-requests/", status_code=201, dependencies=[Depends(check_rate_limiter)]) #Create a request
async def create_friend_request(
    user_id: int,
    body: SendRequestBody,
    _auth_user_id: int = Depends(require_auth_user),
    repo: FriendRepository = Depends(get_friend_repository),
    #session: Session = Depends(get_db),
):
    requester_id = user_id
    receiver_id = body.other
    try:
        await repo.send_request(requester_id, receiver_id)
        return {"ok": True, "message": "Request sent successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{user_id}/friend-requests/{other_id}/", dependencies=[Depends(check_rate_limiter)]) #Update a request
async def update_request_as_requestee(
    user_id: int,
    other_id: int,
    _auth_user_id: int = Depends(require_auth_user),
    repo: FriendRepository = Depends(get_friend_repository),
    #session: Session = Depends(get_db)
):
    try:
        await repo.accept_request(user_id, other_id)
        return {"ok": True, "message": "Request accepted, both are friends now"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.delete("/{user_id}/friend-requests/{other_id}/", dependencies=[Depends(check_rate_limiter)]) #Delete a request
async def delete_request_as_requester(
    user_id: int,
    other_id: int,
    _auth_user_id: int = Depends(require_auth_user),
    repo: FriendRepository = Depends(get_friend_repository),
    #session: Session = Depends(get_db)
):
    try:
        await repo.delete_request(user_id, other_id)
        return {"ok": True, "message": "Request deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Finished friend request, now switch to friendship

@router.get("/{user_id}/friends", dependencies=[Depends(check_rate_limiter)]) #View friend list
async def list_friend(
    user_id: int,
    repo: FriendRepository = Depends(get_friend_repository),
    #session: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # when you wire auth
):
    # assert current_user.name == user_id  # no auth needed for this function
    try:
        rows = await repo.list_friends(user_id)
        return rows
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/{user_id}/friends/{friend_id_or_name}", dependencies=[Depends(check_rate_limiter)]) #Get friend by name/id
async def get_friend_by_id_or_name(
    user_id: int,
    friend_id_or_name: str,  # could be name or id
    repo: FriendRepository = Depends(get_friend_repository),
):
    try:
        if friend_id_or_name.isdigit():
            friend_id = int(friend_id_or_name)
            return await repo.get_friend_by_id(user_id, friend_id)
        else:
            friend_name = friend_id_or_name
            return await repo.get_friend_by_name(user_id, friend_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{user_id}/friends/{friend_id_or_name}", dependencies=[Depends(check_rate_limiter)]) #Delete friend by name/id
async def delete_friendship_by_id_or_name(
    user_id: int,
    friend_id_or_name: str,
    _auth_user_id: int = Depends(require_auth_user),
    repo: FriendRepository = Depends(get_friend_repository),
):
    try:
        if friend_id_or_name.isdigit():
            friend_id = int(friend_id_or_name)
            await repo.delete_friend_by_id(user_id, friend_id)
        else:
            friend_name = friend_id_or_name
            await repo.delete_friend_by_name(user_id, friend_name)
        return {"ok": True, "message": "Deleted successfully, both are no longer friends"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))