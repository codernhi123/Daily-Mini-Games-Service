from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from shared.database import get_db
from user_service.models.game import GameHistoryModel
from fastapi import Depends

class GameHistory:
    """
    Stores past plays and allows querying for history
    (for streaks / consistency boards).
    """

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    async def add_entry(
        self,
        id: Optional[int],
        game_type: str,
        score: int,
        daily_date: datetime,
    ) -> None:
        """
        Add a new history row. Does nothing for guests (id is None).
        """
        if id is None:
            return

        played_at = self._as_utc(daily_date)
        entry = GameHistoryModel(
            user_id=id,
            game_type=game_type,
            score=score,
            played_at=played_at,
        )
        self.session.add(entry)
        self.session.commit()

    async def get_history_for_user(
        self,
        id: int,
        game_type: str,
        days: int = 30,
    ) -> List[GameHistoryModel]:
        """
        Get recent history for a given user and game.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        q = (
            self.session.query(GameHistoryModel)
            .filter(
                GameHistoryModel.user_id == id,
                GameHistoryModel.game_type == game_type,
                GameHistoryModel.played_at >= cutoff,
            )
            .order_by(GameHistoryModel.played_at.asc())
        )
        return list(q.all())


def get_game_history(db: Session = Depends(get_db)) -> GameHistory:
    return GameHistory(db)
