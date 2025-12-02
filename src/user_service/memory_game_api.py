from fastapi import HTTPException, Depends, APIRouter, Request
from pydantic import BaseModel
from typing import Optional
from user_service.auth.jwt_helper import validate_jwt
from user_service.memory_game_service import MemoryGameService
from user_service.game_state import get_game_state, GameState
from user_service.game_history import get_game_history, GameHistory
from user_service.models.leaderboard import get_leaderboard_repository, LeaderboardRepository
from user_service.models.user import UserRepository, get_user_repository
from user_service.models.event import EventRepository, get_event_repository, EventSchemaCreate
from datetime import datetime, timezone

router = APIRouter(prefix="/v2/games/memory", tags=["memory-game"])

def get_memory_service(
    game_state: GameState = Depends(get_game_state),
    game_history: GameHistory = Depends(get_game_history),
    leaderboard: LeaderboardRepository = Depends(get_leaderboard_repository),
    event_repo: EventRepository = Depends(get_event_repository)
) -> MemoryGameService:
    return MemoryGameService(game_state, game_history, leaderboard, event_repo)

class AnswerSubmission(BaseModel):
    session_id: str
    answer: int

@router.post("/start")
async def start_memory_game(
    request: Request, 
    user_id: Optional[int] = None, 
    service: MemoryGameService = Depends(get_memory_service),
    user_repo: UserRepository = Depends(get_user_repository),
    event_repo: EventRepository = Depends(get_event_repository)
    ):
    try:
        token = request.cookies.get("jwt")
        if token and not user_id:
            try:
                payload = validate_jwt(token)
                user_id = int(payload["sub"])
            except ValueError:
                pass  # Invalid/expired token, continue as guest

        await  event_repo.create(EventSchemaCreate(
            when=datetime.now(timezone.utc),
            source="memory_game",
            type="game_start",
            user=str(user_id) if user_id else None,
            payload={}
        ))

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

@router.get("/history/{id}")
async def get_history(id: int, game_type: str = "Memory", repo: GameHistory = Depends(get_game_history)):
    try:
        history = await repo.get_history_for_user(id, game_type, 30)
        return history
    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))
        

