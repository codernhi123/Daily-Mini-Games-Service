from pydantic import BaseModel
from sqlalchemy import select, insert, delete, String, Integer, Sequence
from sqlalchemy.orm import declarative_base, Session, mapped_column, Mapped
from fastapi import Depends

from shared.database import get_db

Base = declarative_base()
user_id_seq = Sequence('user_id_seq')
class User(Base):
    """
    User model used by SQLAlchemy to interact with the database. When you look up a user in the database, you will get an instance of this class back. This is the database's view of users.
    """
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    id: Mapped[int] = mapped_column(Integer, unique=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False) #maybe hash later or do in API

class UserRepository:
    """
    Controls manipulation of the users table.
    """

    def __init__(self, session: Session):
        self.session = session

    # async def create(self, name: str, email: str, password: str) -> User:
    #     if id < 0:
    #         result = self.session.execute(insert(User), [{"name": name, "id": id, "email": email, "password": password}])
    #         self.session.commit()
    #         return User(name=name, id=id, email=email, password=password)
    #     else:
    #         result = self.session.execute(insert(User), [{"name": name, "email": email, "password": password}])
    #         self.session.commit()
    #         return User(name=name, email=email, password=password)

    async def create(self, name: str, email: str, password: str) -> User:
        result = self.session.execute(insert(User), [{"name": name}])
        self.session.commit()
        return User(name=name, email=email, password=password)
        
    async def create_with_id(self, name: str, id: id, email: str, password: str) -> User:
        result = self.session.execute(insert(User), [{"name": name}])
        self.session.commit()
        return User(name=name)
    
    # async def create(self, name: str, id: int, email: str, password: str) -> User:
    #     result = self.session.execute(insert(User), [{"name": name, "id": id, "email": email, "password": password}])
    #     self.session.commit()
    #     return User(name=name, id=id, email=email, password=password)
        
    # async def create(self, name: str, email: str, password: str) -> User:
    #     result = self.session.execute(insert(User), [{"name": name, "email": email, "password": password}])
    #     self.session.commit()
    #     return User(name=name, email=email, password=password)

    async def delete(self, name: str) -> None:
        user = await self.get_by_name(name)
        stmt = delete(User).where(User.name == name)
        result = self.session.execute(stmt)
        self.session.commit()
        return result

    async def get_all(self) -> list[User]:
        """Get all users"""
        users = self.session.scalars(select(User)).all()
        return users

    async def get_by_name(self, name: str) -> User: #could update to be more efficient for larger tables
        """Get user by name"""
    
    async def get_by_id(self, id: int) -> User:
        """Get user by id"""
        user = next((u for u in await self.get_all() if u.id == id), None)
        return user

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

# class UserDisplaySchema(BaseModel):
#     """
#     The application's view of users. This is how the API represents users (as opposed to how the database represents them).
#     """
#     name: str
#     id: int 
#     email: str
#     # password: str | None = None

#     @classmethod
#     def from_db_model(cls, user: User) -> "UserDisplaySchema":
#         """Display a UserDisplaySchema from a User"""
#         return cls(name=user.name, id=user.id, email=user.email)
#     # Vid=getattr(user, "id", None),
    
# class UserInputSchema(BaseModel):
#     """
#     The application's view of users. This is how the API represents users (as opposed to how the database represents them).
#     """
#     name: str
#     # id: int | None = None
#     email: str
#     password: str  #security risk, seperate into two create vs read schema

#     @classmethod
#     def from_db_model(cls, user: User) -> "UserInputSchema":
#         """Create a UserInputSchema from a User"""
#         return cls(name=user.name, email=user.email, password=user.password)


class UserSchema(BaseModel):
    """
    The application's view of users. This is how the API represents users (as opposed to how the database represents them).
    """
    name: str
    id: int
    email: str
    password: str #security risk, sperate into two create vs read schema

    @classmethod
    def from_db_model(cls, user: User) -> "UserSchema":
        """Create a UserSchema from a User"""
    #    return cls(name=user.name, id=getattr(user, "id", None), email=getattr(user, "email", None), password=getattr(user, "password", None))
        return cls(name=user.name, id=user.id, email=user.email, password=user.password)
