from pydantic import BaseModel
from sqlalchemy import select, insert, delete, String, Integer, Sequence
from sqlalchemy.orm import declarative_base, Session, mapped_column, Mapped
from fastapi import Depends

from shared.database import get_db

Base_v1 = declarative_base()
user_id_seq_v1 = Sequence('user_id_seq_v1')
class User_v1(Base_v1):
    """
    User model used by SQLAlchemy to interact with the database. When you look up a user in the database, you will get an instance of this class back. This is the database's view of users.
    """
    __tablename__ = "users_v1"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    id: Mapped[int] = mapped_column(Integer, unique=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False) #maybe hash later, here or in API

class UserRepository_v1:
    """
    Controls manipulation of the users_v1 table.
    """

    def __init__(self, session: Session):
        self.session = session

    async def create(self, name: str, email: str, password: str) -> User_v1:
        try:
            self.session.execute(insert(User_v1), [{"name": name, "email": email, "password": password}])
            self.session.commit()
            return User_v1(name=name, email=email, password=password)
        except Exception as e:
            self.session.rollback()
            raise e
        
    async def create_with_id(self, name: str, id: id, email: str, password: str) -> User_v1:
        try:
            self.session.execute(insert(User_v1), [{"name": name, "id": id, "email": email, "password": password}])
            self.session.commit()
            return User_v1(name=name, id=id, email=email, password=password)
        except Exception as e:
            self.session.rollback()
            raise e
    
    async def delete(self, name: str) -> None:
        await self.get_by_name(name)
        stmt = delete(User_v1).where(User_v1.name == name)
        result = self.session.execute(stmt)
        self.session.commit()
        return result

    async def get_all(self) -> list[User_v1]:
        """Get all users"""
        users_v1 = self.session.scalars(select(User_v1)).all()
        return users_v1

    async def get_by_name(self, name: str) -> User_v1 | None:
        """Get user by name"""
        stmt = select(User_v1).where(User_v1.name == name)
        result = self.session.scalar(stmt)
        return result
    
    async def get_by_id(self, id: int) -> User_v1:
        """Get user by id"""
        user_v1 = next((u for u in await self.get_all() if u.id == id), None)
        return user_v1

def get_user_repository_v1(db: Session = Depends(get_db)) -> UserRepository_v1:
    return UserRepository_v1(db)

class UserSchema_v1(BaseModel):
    """
    The application's view of users. This is how the API represents users (as opposed to how the database represents them).
    """
    name: str
    id: int
    email: str
    password: str #security risk, potentially seperate into two create vs read schema

    @classmethod
    def from_db_model(cls, u: User_v1) -> "UserSchema_v1":
        """Create a UserSchema from a User"""
        return cls(name=u.name, id=u.id, email=u.email, password=u.password)