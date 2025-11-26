from fastapi import Depends, HTTPException, APIRouter
from datetime import datetime
#from .models.rate_limiter import check_rate_limiter
#from user_service.auth.jwt_helper import validate_jwt

from .models.leaderboard import LeaderboardRepository, get_leaderboard_repository
from .models.friend import get_friend_repository, FriendRepository

router = APIRouter(prefix="/leaderboard", tags=["leaderboards"])

@router.get("/view-global-leaderboard/{game_name}/{when}", status_code=200)
async def get_global_leaderboard(
    game_name: str,
    when: datetime,
    repo: LeaderboardRepository = Depends(get_leaderboard_repository)
):
    rows = await repo.view_global_scores(game_name, when)
    return [
        {
            "user_name": qr.user_name,
            "scores": qr.scores,
        }
        for qr in rows
    ]

@router.get("/view-friend-leaderboard/{user_id}/{game_name}/{when}", status_code=200)
async def get_friend_leaderboard(
    user_id: int,
    game_name: str,
    when: datetime,
    repo: LeaderboardRepository = Depends(get_leaderboard_repository),
    friend_repo: FriendRepository = Depends(get_friend_repository)
):
    rows = await repo.view_friend_scores(user_id, game_name, when, friend_repo)
    return [
        {
            "user_name": qr.user_name,
            "scores": qr.scores,
        }
        for qr in rows
    ]

@router.get("/inactive/{user_id}/{game_name}/{when}", status_code=200)
async def get_inactive_leaderboard(
    user_id: int,
    game_name: str,
    when: datetime,
    repo: LeaderboardRepository = Depends(get_leaderboard_repository),
    friend_repo: FriendRepository = Depends(get_friend_repository)
):
    rows = await repo.view_inactive_scores(user_id, game_name, when, friend_repo)
    return [
        {
            "user_id": qr
        }
        for qr in rows
    ]

@router.post("/update-leader-board/", status_code=200)
async def update_leader_board(
    user_id: int,
    user_name: str,
    game_name: str,
    scores: int,
    when: datetime,
    next_date: datetime,
    repo: LeaderboardRepository = Depends(get_leaderboard_repository)
):
    try:
        await repo.update_scores(user_id, user_name, scores, game_name, when, next_date)
        return {"ok": True, "message": "Updated latest scores successfully"}
    except Exception as e:
        raise HTTPException(status_code = 400, detail=str(e))