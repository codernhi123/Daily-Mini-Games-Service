from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from fastapi import Depends
from sqlalchemy import String, Integer, select, insert, update, and_, or_, ForeignKey, UniqueConstraint, Index, delete, CheckConstraint
from sqlalchemy import DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.sql import func
#from sqlalchemy import case

from .user import Base 
from .user import User
#from shared.database import get_db

class FriendRequest(Base):
    __tablename__ = "friend_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key = True, autoincrement = True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, server_default=text("'pending'"), nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable = False)
    __table_args__ = (
        UniqueConstraint("requester_id", "receiver_id", name="uq_friend_request_pair"),
        Index("ix_friend_requests_receiver_status", "receiver_id", "status"),
        
        CheckConstraint("requester_id <> receiver_id", name="ck_fr_not_self"),
    )

class Friendship(Base):
    __tablename__ = "friendships"
    user_a_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    user_b_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_friend_pair"),
        CheckConstraint("user_a_id <> user_b_id", name="ck_fs_not_self"),
        CheckConstraint("user_a_id < user_b_id", name="ck_fs_canonical_order"),
    )

class FriendRepository:
    def __init__(self , session:Session):
        self.session = session

    # Helper functions STARTED
    def _ordered_ids(self, a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)
    
    def _get_request_by_pair(self, requester_id: int, receiver_id: int):
        stmt = select(FriendRequest).where(
            and_(
                FriendRequest.requester_id == requester_id,
                FriendRequest.receiver_id == receiver_id,
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def _get_pending_request_either_direction(self, a: int, b: int):
        # for duplicate prevention
        stmt = select(FriendRequest.id).where(
            and_(FriendRequest.status == "pending"),
            or_(
                and_(FriendRequest.requester_id == a, FriendRequest.receiver_id == b),
                and_(FriendRequest.requester_id == b, FriendRequest.receiver_id == a),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()
    # ENDED

    async def view_request_incoming(self, user_id: int):
        stmt = select(FriendRequest).where(
            and_(FriendRequest.receiver_id == user_id, FriendRequest.status == "pending")
        )
        return self.session.scalars(stmt).all()
    
    async def view_request_outgoing(self, user_id: int):
        stmt = select(FriendRequest).where(
            and_(FriendRequest.requester_id == user_id, FriendRequest.status == "pending")
        )
        return self.session.scalars(stmt).all()
    
    async def send_request(self, requester_id: int, receiver_id: int):
        try:
            if receiver_id == requester_id:
                raise ValueError("Cannot make friend with yourself")
            
            a, b = self._ordered_ids(requester_id, receiver_id)
            exists = self.session.get(Friendship, (a, b))
            if exists:
                raise ValueError("Already been friends")
            
            pending_stmt = self._get_pending_request_either_direction(requester_id, receiver_id)
            if pending_stmt:
                raise ValueError("A pending request already exists between these users")
            
            new_fr = FriendRequest(requester_id = requester_id, receiver_id = receiver_id, status="pending")
            self.session.add(new_fr)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    async def accept_request(self, acting_user_id: int, requester_id: int):
        try:
            fr = self._get_request_by_pair(requester_id, acting_user_id)
            if not fr or fr.status != "pending" or fr.receiver_id != acting_user_id:
                raise ValueError("No pending request to accept")
            
            a, b = self._ordered_ids(requester_id, acting_user_id)
            if not self.session.get(Friendship, (a, b)):
                self.session.add(Friendship(user_a_id=a, user_b_id=b))

            fr.status = "accepted"
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    async def delete_request(self, acting_user_id: int, receiver_id: int):
        try:
            fr = self._get_request_by_pair(acting_user_id, receiver_id)
            if not fr or fr.status != "pending":
                raise ValueError("No request to cancel")
            
            self.session.delete(fr)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    async def pending_list(self, user_id: int):
        stmt = select(FriendRequest).where(and_(FriendRequest.status == "pending", FriendRequest.receiver_id == user_id))
        return self.session.scalars(stmt).all()
    
    async def list_friends(self, user_id: int) -> list[int]:
        stmt = select(Friendship).where(or_(Friendship.user_a_id == user_id, Friendship.user_b_id == user_id))
        fr_status = self.session.scalars(stmt).all()
        return [x.user_b_id if x.user_a_id == user_id else x.user_a_id for x in fr_status]
    
    async def get_friend_by_name(self, user_id: int, friend_name: str) -> str:
        stmt = (
            select(User.id)
            .join(
                Friendship,
                or_(
                    Friendship.user_a_id == User.id,
                    Friendship.user_b_id == User.id,
                )
            )
            .where(
                #acting user
                or_(
                    Friendship.user_a_id == user_id,
                    Friendship.user_b_id == user_id,
                )
            )
            .where(User.name == friend_name) # other user’s name matches friend_name
            .where(User.id != user_id) # don’t accidentally match yourself if same name/id
        )

        result = self.session.execute(stmt)
        fr_status =  result.scalar_one_or_none()

        if not fr_status:
            return f"{user_id} and {friend_name} are not friends"
        else:
            return f"{user_id} and {friend_name} are friends"
    
    async def get_friend_by_id(self, user_id: int, friend_id: int) -> str:
        a, b = self._ordered_ids(user_id, friend_id)

        stmt = select(Friendship).where(
            and_(Friendship.user_a_id == a, Friendship.user_b_id == b)
        )

        result = self.session.execute(stmt)
        fr_status =  result.scalar_one_or_none()

        if not fr_status:
            return f"{user_id} and {friend_id} are not friends"
        else:
            return f"{user_id} and {friend_id} are friends"
        
    async def delete_friend_by_name(self, user_id: int, friend_name: str):
        try:
            friend_id_stmt = (
                select(User.id)
                .join(
                    Friendship,
                    or_(
                        Friendship.user_a_id == User.id,
                        Friendship.user_b_id == User.id,
                    ),
                )
                .where(
                    or_(
                        Friendship.user_a_id == user_id,
                        Friendship.user_b_id == user_id,
                    )
                )
                .where(User.name == friend_name)
                .where(User.id != user_id)
            )

            friend_id = self.session.execute(friend_id_stmt).scalar_one_or_none()
            
            if friend_id is None:
                raise ValueError(f"No friendship found between {user_id} and {friend_name}")

            a, b = self._ordered_ids(user_id, friend_id)
            fs = self.session.get(Friendship, (a, b))

            if not fs:
                raise ValueError("Friendship does not exist to be deleted")
            
            self.session.delete(fs)
            self.session.execute(
                delete(FriendRequest).where(
                    or_(
                        and_(FriendRequest.requester_id == a, FriendRequest.receiver_id == b),
                        and_(FriendRequest.requester_id == b, FriendRequest.receiver_id == a),
                    )
                )
            )

            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    async def delete_friend_by_id(self, user_id: int, friend_id: int):
        try:
            if user_id == friend_id:
                raise ValueError("Cannot unfriend yourself")
            
            a, b = self._ordered_ids(user_id, friend_id)
            fs = self.session.get(Friendship, (a, b))
            if not fs:
                raise ValueError("Friendship does not exist to be deleted")
            
            self.session.delete(fs)
            self.session.execute(
                delete(FriendRequest).where(
                    or_(
                        and_(FriendRequest.requester_id == a, FriendRequest.receiver_id == b),
                        and_(FriendRequest.requester_id == b, FriendRequest.receiver_id == a),
                    )
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

def _get_db_dep():
    # defer the import so env/engine are ready
    from shared.database import get_db as real_get_db
    yield from real_get_db()

def get_friend_repository(db: Session = Depends(_get_db_dep)) -> FriendRepository:
    return FriendRepository(db)