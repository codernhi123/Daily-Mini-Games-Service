from fastapi import HTTPException, Depends, APIRouter
from pydantic import BaseModel
from typing import Optional
from user_service.memory_game_service import MemoryGameService
from user_service.game_state import get_game_state
from user_service.game_history import get_game_history
from user_service.leaderboards import get_leaderboards

router = APIRouter(prefix="/v2/games/memory", tags=["memory-game"])


_memory_service: Optional[MemoryGameService] = None

def get_memory_service() -> MemoryGameService:
    global _memory_service
    if _memory_service is None:
        game_state = get_game_state()
        game_history = get_game_history()
        leaderboards = get_leaderboards()
        _memory_service = MemoryGameService(game_state, game_history, leaderboards)
    return _memory_service

class AnswerSubmission(BaseModel):
    session_id: str
    answer: int

# def get_complete_memory_service(
#         game_state = Depends(get_game_state), game_history = Depends(get_game_history), leaderboards = Depends(get_leaderboards)
# ) -> MemoryGameService:
#     return MemoryGameService(game_state, game_history, leaderboards)

@router.post("/start")
async def start_memory_game(user_id: Optional[int] = None, service: MemoryGameService = Depends(get_memory_service)):
    try:
        result = await service.start_game(user_id)
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

