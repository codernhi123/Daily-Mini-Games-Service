from datetime import datetime
from sqlalchemy import (
    DateTime,
    Integer,
    String,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from user_service.models.user import Base


class GameStateModel(Base):
    """
    Per-user state for each game type (e.g. 'memory', 'trivia').
    Controls once-per-day restriction.
    """
    __tablename__ = "game_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_type: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # When the user last played this game
    last_played: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # When they are next allowed to play (midnight UTC, typically)
    next_play_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "game_type", name="uq_game_state_user_game"),
        Index("ix_game_state_user_game", "user_id", "game_type"),
    )


class GameHistoryModel(Base):
    """
    History of game plays for streaks / consistency board.
    One row per play.
    """
    __tablename__ = "game_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Exact datetime of play (UTC)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index("ix_game_history_user_game_date", "user_id", "game_type", "played_at"),
    )
