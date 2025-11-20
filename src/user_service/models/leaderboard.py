from datetime import datetime
from fastapi import Depends
from sqlalchemy import String, Integer, select, and_, ForeignKey, Index, delete, CheckConstraint
from sqlalchemy import DateTime, text, func
from sqlalchemy.orm import Mapped, mapped_column, Session #todo: consider change to AsyncSession
from .user import Base 
from .friend import FriendRepository
from dotenv import load_dotenv
load_dotenv()

class Leaderboard(Base):
    __tablename__ = "leader_board"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete = "CASCADE"), index = True, nullable = False)
    user_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    scores: Mapped[int] = mapped_column(Integer, nullable = False)
    game_name: Mapped[str] = mapped_column(String, nullable = False)
    when: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable = False)
    __table_args__ = (
        Index("ix_leader_board_name_scores_game_name", "user_name", "scores", "game_name"),
        CheckConstraint("scores >= 0", name="ck_leaderboard_scores_positive"),
    )

class LeaderboardRepository:
    def __init__(self, session:Session):
        self.session = session
    
    def _delete_expired_data(self, game_name: str, current_date: datetime):
        today = current_date.date()

        stmt = delete(Leaderboard).where(
            and_(
                Leaderboard.game_name == game_name,
                func.date(Leaderboard.when) < today
            )
        )
        self.session.execute(stmt)
        self.session.commit()

    def _get_data_today(self, game_name: str, current_date: datetime):
        self._delete_expired_data(game_name, current_date)

        stmt = select(Leaderboard).where(
            and_(
                func.date(Leaderboard.when) == current_date.date(), 
                Leaderboard.game_name == game_name
            )
        ).order_by(Leaderboard.scores.desc())
        
        return self.session.execute(stmt).scalars().all()

    async def view_global_scores(self, game_name: str, current_date: datetime):
        self._delete_expired_data(game_name, current_date)
        return self._get_data_today(game_name, current_date)

    async def view_friend_scores(self, user_id: int, game_name: str, current_date: datetime, repo: FriendRepository):
        self._delete_expired_data(game_name, current_date)
        friend_ids = await repo.list_friends(user_id)

        friend_ids.append(user_id)

        stmt = select(Leaderboard).where(
            and_(
                Leaderboard.user_id.in_(friend_ids),
                Leaderboard.game_name == game_name,
                func.date(Leaderboard.when) == current_date.date()
            )
        ).order_by(Leaderboard.scores.desc())

        return self.session.execute(stmt).scalars().all()

    async def update_scores(self, user_id: int, user_name: str, scores: int, game_name: str, current_date: datetime, next_date: datetime):
        self._delete_expired_data(game_name, current_date)
        try:
            stmt = select(Leaderboard).where(
                and_(
                    Leaderboard.user_id == user_id, 
                    Leaderboard.game_name == game_name,
                    func.date(Leaderboard.when) == current_date.date()
                )
            )
            result = self.session.execute(stmt).scalar_one_or_none()

            if result:
                raise ValueError("Already played today, cannot update score until tommorrow")
            
            new_scores = Leaderboard(user_id = user_id, user_name = user_name, scores = scores, game_name = game_name, when = current_date)
            self.session.add(new_scores)
            self.session.commit()

        except Exception:
            self.session.rollback()
            raise
    
def _get_db_lb():
    from shared.database import get_db as real_get_db
    yield from real_get_db()

def get_leaderboard_repository(db: Session = Depends(_get_db_lb)) -> LeaderboardRepository:
    return LeaderboardRepository(db)