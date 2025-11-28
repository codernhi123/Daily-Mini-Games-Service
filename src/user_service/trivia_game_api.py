from fastapi import HTTPException, Depends, APIRouter, Request
from pydantic import BaseModel
from typing import Optional
from user_service.auth.jwt_helper import validate_jwt
from user_service.models.user import UserRepository, get_user_repository
from user_service.trivia_game_service import TriviaGameService
from user_service.game_state import GameState, get_game_state
from user_service.game_history import GameHistory, get_game_history
from user_service.models.leaderboard import LeaderboardRepository, get_leaderboard_repository
from user_service.models.event import EventRepository, get_event_repository, EventSchemaCreate
from datetime import datetime, timezone

router = APIRouter(prefix="/v2/games/trivia", tags=["trivia-game"])

# _trivia_service: Optional[TriviaGameService] = None

# def get_trivia_service() -> TriviaGameService:
#     global _trivia_service
#     if _trivia_service is None:
#         game_state = get_game_state()
#         game_history = get_game_history()
#         leaderboards = get_leaderboard_repository()
#         _trivia_service = TriviaGameService(game_state, game_history, leaderboards)
#     return _trivia_service

def get_trivia_service(
    game_state: GameState = Depends(get_game_state),
    game_history: GameHistory = Depends(get_game_history),
    leaderboard: LeaderboardRepository = Depends(get_leaderboard_repository),
    event_repo: EventRepository = Depends(get_event_repository)
) -> TriviaGameService:
    return TriviaGameService(game_state, game_history, leaderboard, event_repo)

class AnswerSubmission(BaseModel):
    session_id: str
    answer_index: int

@router.post("/start")
async def start_trivia_game(
    request: Request, 
    user_id: Optional[int] = None,
    service: TriviaGameService = Depends(get_trivia_service),
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
            source="trivia_game",
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
        result = await service.submit_answer(submission.session_id, submission.answer_index)
    
        # if result.get("game_over"):
        #     session = service.active_sessions.get(submission.session_id)
        #     if session and session.get("id"):
        #         await  event_repo.create(EventSchemaCreate(
        #             when=datetime.now(timezone.utc),
        #             source="trivia_game",
        #             type="game_complete",
        #             user=str(session["id"]),
        #             payload={
        #                 "streak": session.get("streak", 0),
        #                 "best_streak": session.get("best_streak", 0),
        #                 "score": result.get("final_score", 0)
        #             }
        #         ))
            
        return result
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
    
@router.get("/history/{id}")
async def get_history(id: int, game_type: str = "Trivia", repo: GameHistory = Depends(get_game_history)):
    try:
        history = await repo.get_history_for_user(id, game_type, 30)
        return history
    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))