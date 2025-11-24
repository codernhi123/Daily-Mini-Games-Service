from fastapi import HTTPException, Depends, APIRouter, Request
from pydantic import BaseModel
from typing import Optional
from user_service.auth.jwt_helper import validate_jwt
from user_service.memory_game_service import MemoryGameService
from user_service.game_state import get_game_state, GameState
from user_service.game_history import get_game_history, GameHistory
from user_service.models.leaderboard import get_leaderboard_repository, LeaderboardRepository
from user_service.models.user import UserRepository, get_user_repository

router = APIRouter(prefix="/v2/games/memory", tags=["memory-game"])

#old stuff
# _memory_service: Optional[MemoryGameService] = None

# def get_memory_service() -> MemoryGameService:
#     global _memory_service
#     if _memory_service is None:
#         game_state = get_game_state()
#         game_history = get_game_history()
#         leaderboards = get_leaderboard_repository()
#         _memory_service = MemoryGameService(game_state, game_history, leaderboards)
#     return _memory_service

def get_memory_service(
    game_state: GameState = Depends(get_game_state),
    game_history: GameHistory = Depends(get_game_history),
    leaderboard: LeaderboardRepository = Depends(get_leaderboard_repository)
) -> MemoryGameService:
    return MemoryGameService(game_state, game_history, leaderboard)

class AnswerSubmission(BaseModel):
    session_id: str
    answer: int

@router.post("/start")
async def start_memory_game(
    request: Request, 
    user_id: Optional[int] = None, 
    service: MemoryGameService = Depends(get_memory_service),
    user_repo: UserRepository = Depends(get_user_repository)
    ):
    try:
        token = request.cookies.get("jwt")
        if token and not user_id:
            try:
                payload = validate_jwt(token)
                user_id = int(payload["sub"])
            except:
                pass  # Invalid/expired token, continue as guest
        
        user_name = None
        if user_id:
            user = await user_repo.get_by_id(user_id)
            if user:
                user_name = user.name
            
        result = await service.start_game(user_id, user_name)
        return result
    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))
    
@router.post("/display/{session_id}")
async def display_images(session_id: str, service: MemoryGameService = Depends(get_memory_service)):
    try:
        result = await service.display_and_get_question(session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code = 404, detail = str(e))
    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))
    
@router.post("/submit")
async def submit_answer(submission: AnswerSubmission, service: MemoryGameService = Depends(get_memory_service)):
    try:
        result = await service.submit_answer(submission.session_id, submission.answer)
        return result
    except ValueError as e:
        raise HTTPException(status_code = 404, detail = str(e))
    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))
    
@router.get("/can_play/{id}")
async def check_can_play(id: int, service: MemoryGameService = Depends(get_memory_service)):
    try:
        result = await service.can_play_today(id)
        return result
    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))


