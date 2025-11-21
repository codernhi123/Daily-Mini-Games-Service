from fastapi import HTTPException, Depends, APIRouter
from pydantic import BaseModel
from typing import Optional
from user_service.trivia_game_service import TriviaGameService
from user_service.game_state import get_game_state
from user_service.game_history import get_game_history
from user_service.models.leaderboard import get_leaderboard_repository

router = APIRouter(prefix="/v2/games/trivia", tags=["trivia-game"])

_trivia_service: Optional[TriviaGameService] = None

def get_trivia_service() -> TriviaGameService:
    global _trivia_service
    if _trivia_service is None:
        game_state = get_game_state()
        game_history = get_game_history()
        leaderboards = get_leaderboard_repository()
        _trivia_service = TriviaGameService(game_state, game_history, leaderboards)
    return _trivia_service

class AnswerSubmission(BaseModel):
    session_id: str
    answer_index: int

@router.post("/start")
async def start_trivia_game(
    user_id: Optional[int] = None,
    service: TriviaGameService = Depends(get_trivia_service)
):
    try:
        result = await service.start_game(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/question/{session_id}")
async def get_question(
    session_id: str,
    service: TriviaGameService = Depends(get_trivia_service)
):
    try:
        return await service.get_current_question(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit")
async def submit_trivia_answer(
    submission: AnswerSubmission,
    service: TriviaGameService = Depends(get_trivia_service)
):
    try:
        return await service.submit_answer(submission.session_id, submission.answer_index)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/can_play/{id}")
async def check_can_play(
    id: int,
    service: TriviaGameService = Depends(get_trivia_service)
):
    try:
        return await service.can_play_today(id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))