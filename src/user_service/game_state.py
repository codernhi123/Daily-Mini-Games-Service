from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from shared.database import get_db
from user_service.models.game import GameStateModel


class GameState:
    """
    Handles per-user, per-game once-per-day restriction.
    """

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    async def get_state(self, id: Optional[int], game_type: str) -> Dict[str, Any]:
        """
        Return current state for a user & game_type.

        For guests (id is None), always allow play and don't persist anything.
        """
        now = datetime.now(timezone.utc)

        if id is None:
            return {
                "can_play": True,
                "last_played": None,
                "next_play_time": None,
                "now": now,
            }

        state = (
            self.session.query(GameStateModel)
            .filter(
                GameStateModel.user_id == id,
                GameStateModel.game_type == game_type,
            )
            .one_or_none()
        )

        if state is None:
            return {
                "can_play": True,
                "last_played": None,
                "next_play_time": None,
                "now": now,
            }

        can_play = now >= state.next_play_time
        return {
            "can_play": can_play,
            "last_played": state.last_played,
            "next_play_time": state.next_play_time,
            "now": now,
        }

    async def update_state(
        self,
        id: Optional[int],
        game_type: str,
        played_date: datetime,
        next_play_time: datetime,
    ) -> None:
        """
        Update last_played and next_play_time after a completed game.
        For guests (id is None), does nothing.
        """
        if id is None:
            return

        played_date = self._as_utc(played_date)
        next_play_time = self._as_utc(next_play_time)

        state = (
            self.session.query(GameStateModel)
            .filter(
                GameStateModel.user_id == id,
                GameStateModel.game_type == game_type,
            )
            .one_or_none()
        )

        if state is None:
            state = GameStateModel(
                user_id=id,
                game_type=game_type,
                last_played=played_date,
                next_play_time=next_play_time,
            )
            self.session.add(state)
        else:
            state.last_played = played_date
            state.next_play_time = next_play_time

        self.session.commit()


def get_game_state(db: Session | None = None) -> GameState:
    """
    kept the get_game_state() signature so memory_game_api keeps working, but now it actually uses the DB.
    """
    if db is None:
        db = next(get_db())
    return GameState(db)
