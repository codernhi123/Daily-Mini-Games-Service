from datetime import datetime
from fastapi import Depends
from sqlalchemy import String, Integer, select, insert, update, and_, or_, ForeignKey, UniqueConstraint, Index, delete
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.sql import func

from .user import Base 
from shared.database import get_db

class FriendRequest(Base):
    __tablename__ = "friend_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key = True, autoincrement = True)
    requester: Mapped[str] = mapped_column(ForeignKey("users.name", ondelete = "CASCADE"), index = True, nullable = False)
    receiver: Mapped[str] = mapped_column(ForeignKey("users.name", ondelete = "CASCADE"), index = True, nullable = False)
    status: Mapped[str] = mapped_column(String, default = "pending", nullable = False)
    created_at: Mapped[datetime] = mapped_column(server_default = func.now(), nullable = False)

    __table_args__ = (
        UniqueConstraint("requester", "receiver", name="uq_friend_request_pair"),
        Index("ix_friend_requests_receiver_status", "receiver", "status"),
    )

class Friendship(Base):
    __tablename__ = "friendships"
    user_a: Mapped[str] = mapped_column(ForeignKey("users.name", ondelete="CASCADE"), primary_key = True)
    user_b: Mapped[str] = mapped_column(ForeignKey("users.name", ondelete="CASCADE"), primary_key = True)

    __table_args__ = (
        UniqueConstraint("user_a", "user_b", name="uq_friend_pair"),
    )

class FriendRepository:
    def __init__(self , session:Session):
        self.session = session

    def _ordered(self, u1: str, u2: str) -> tuple[str, str]:
        return (u1, u2) if u1 < u2 else (u2, u1)
    
    async def view_request_incoming(self, user_name: str):
        stmt = select(FriendRequest).where(
            and_(FriendRequest.receiver == user_name, FriendRequest.status == "pending")
        )
        return self.session.scalars(stmt).all()
    
    async def view_request_outgoing(self, user_name: str):
        stmt = select(FriendRequest).where(
            and_(FriendRequest.requester == user_name, FriendRequest.status == "pending")
        )
        return self.session.scalars(stmt).all()
    
    async def send_request(self, requester:str, receiver:str):
        try:
            if receiver == requester:
                raise ValueError("Cannot make friend with yourself")
            
            a, b = self._ordered(requester, receiver)
            exists = self.session.get(Friendship, (a, b))
            if exists:
                raise ValueError("Already been friends")
            
            new_fr = FriendRequest(requester = requester, receiver = receiver)
            self.session.add(new_fr)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    async def delete_request(self, requester:str, request_id:int):
        try:
            current_fr = self.session.get(FriendRequest, request_id)
            if not current_fr or current_fr.status != "pending" or current_fr.requester!=requester:
                raise ValueError("Cannot delete request")
            
            self.session.delete(current_fr)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    async def pending_list(self, user: str):
        stmt = select(FriendRequest).where(and_(FriendRequest.status == "pending", FriendRequest.receiver == user))
        return self.session.scalars(stmt).all()
    
    async def accept_request(self, request_id: int, user: str):
        try:
            new_fr = self.session.get(FriendRequest, request_id)
            if not new_fr or new_fr.status != "pending" or new_fr.receiver!=user:
                raise ValueError("Cannot friend")
            a, b = self._ordered(new_fr.requester, new_fr.receiver)
            self.session.execute(insert(Friendship).values(user_a = a, user_b = b))
            self.session.execute(
                update(FriendRequest).where(FriendRequest.id == request_id).values(status = "accepted")
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
    
    async def delete_friend_by_name(self, user_a: str, user_b: str):
        try:
            if user_a == user_b:
                raise ValueError("Cannot unfriend yourself")
            
            a, b = self._ordered(user_a, user_b)
            fs = self.session.get(Friendship, (a, b))
            if not fs or fs.user_a != a or fs.user_b != b:
                raise ValueError("Friendship does not exist to be deleted")
            
            self.session.delete(fs)

            self.session.execute(
                delete(FriendRequest).where(
                    or_(
                        and_(FriendRequest.requester == a, FriendRequest.receiver == b),
                        and_(FriendRequest.requester == b, FriendRequest.receiver == a),
                    )
                )
            )

            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    async def list_friends(self, user: str) -> list[str]:
        stmt = select(Friendship).where(or_(Friendship.user_a == user, Friendship.user_b == user))
        fr_status = self.session.scalars(stmt).all()
        return [x.user_b if x.user_a == user else x.user_a for x in fr_status]
    
    async def get_friend_by_name(self, user_a: str, user_b: str) -> str:
        a, b = self._ordered(user_a, user_b)

        stmt = select(Friendship).where(
            and_(Friendship.user_a == a, Friendship.user_b == b)
        )

        result = self.session.execute(stmt)
        fr_status =  result.scalar_one_or_none()

        if not fr_status:
            return f"{user_a} and {user_b} are not friends"
        else:
            return f"{user_a} and {user_b} are friends"

def get_friend_repository(db: Session = Depends(get_db)) -> FriendRepository:
    return FriendRepository(db)