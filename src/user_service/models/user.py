from pydantic import BaseModel, field_validator
from sqlalchemy import select, insert, delete, String, Integer, Sequence
from sqlalchemy.orm import declarative_base, Session, mapped_column, Mapped
from fastapi import Depends
from passlib.context import CryptContext
from typing import Optional
from shared.database import get_db

Base = declarative_base()
user_id_seq = Sequence('user_id_seq')
class User(Base):
    """
    User model used by SQLAlchemy to interact with the database. When you look up a user in the database, you will get an instance of this class back. This is the database's view of users.
    """
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String, unique=True)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

hashed_crypt = CryptContext(schemes=["bcrypt"], deprecated = "auto")

def password_hash(password: str) -> str:
    if password.startswith("$2b$"):
        return password
    return hashed_crypt.hash(password)

def password_verification(regular_password: str, hashed_password: str) -> bool:
    return hashed_crypt.verify(regular_password, hashed_password)
class UserRepository:
    """
    Controls manipulation of the users table.
    """

    def __init__(self, session: Session):
        self.session = session

    async def create(self, name: str, email: str, password: str, tier: int) -> User:
        try:
            secret_password = password_hash(password)
            self.session.execute(insert(User), [{"name": name, "email": email, "password": secret_password, "tier": tier}])
            self.session.commit()
            return User(name=name, email=email, password=secret_password, tier=tier)
        except Exception as e:
            self.session.rollback()
            raise e
        
    async def create_with_id(self, name: str, id: id, email: str, password: str, tier: int) -> User:
        try:
            secret_password = password_hash(password)
            self.session.execute(insert(User), [{"name": name, "id": id, "email": email, "password": secret_password, "tier": tier}])
            self.session.commit()
            return User(name=name, id=id, email=email, password=secret_password, tier=tier)
        except Exception as e:
            self.session.rollback()
            raise e
    
    async def delete(self, name: str) -> None:
        await self.get_by_name(name)
        stmt = delete(User).where(User.name == name)
        result = self.session.execute(stmt)
        self.session.commit()
        return result
    
    async def delete_by_id(self, id: int) -> None:
        await self.get_by_name(id)
        stmt = delete(User).where(User.id == id)
        result = self.session.execute(stmt)
        self.session.commit()
        return result

    async def get_all(self) -> list[User]:
        """Get all users"""
        users = self.session.scalars(select(User)).all()
        return users

    async def get_by_name(self, name: str) -> User | None:
        """Get user by name"""
        stmt = select(User).where(User.name == name)
        result = self.session.scalar(stmt)
        return result
    
    async def get_by_id(self, id: int) -> User | None:
        """Get user by id"""
        stmt = select(User).where(User.id == id)
        result = self.session.scalar(stmt)
        return result
    
    async def get_by_email(self, email: str) -> User | None:
        """Get user by id"""
        stmt = select(User).where(User.email == email)
        result = self.session.scalar(stmt)
        return result

    async def update_user(self, id: int, **kwargs) -> User:
        try:
            user = await self.get_by_id(id)
            if not user:
                raise ValueError("User not found")
            
            if 'name' in kwargs and kwargs['name'] is not None:
                if kwargs['name'] != user.name:
                    existing_name = await self.get_by_name(kwargs['name'])
                    if existing_name:
                        raise ValueError("Name already exists")
                    user.name = kwargs['name']
            if 'email' in kwargs and kwargs['email'] is not None:
                if kwargs['email'] != user.email:
                    existing_email = await self.get_by_email(kwargs['email'])
                    if existing_email:
                        raise ValueError("Email already exists")
                    user.email = kwargs['email']
            if 'tier' in kwargs and kwargs['tier'] is not None:
                user.tier = kwargs['tier']
            self.session.commit()
            return user
        except Exception as e:
            self.session.rollback()
            raise e
        
    async def update_password(self, id: int, password: str) -> User:
        try:
            user = await self.get_by_id(id)
            if not user:
                raise ValueError("User not found")

            hashed_password = password_hash(password)
            user.password = hashed_password
            self.session.commit()
            return user
        except Exception as e:
            self.session.rollback()
            raise e

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

class UserSchemaCreate(BaseModel):
    """
    The application's view of users. This is how the API represents users (as opposed to how the database represents them).
    """
    name: str
    id: int
    email: str
    password: str 
    tier: int=1

    @field_validator('name', 'email', 'password')
    @classmethod
    def no_empty_strings(cls, v):
        if v is not None:
            stripped = v.strip()
            if stripped == "":
                raise ValueError("Fields cannot be empty or whitespace")
            return stripped
        return v
    
    @field_validator('tier')
    @classmethod
    def valid_tier(cls, v):
        if v < 1:
            raise ValueError("Tier must be at least 1")
        return v

class UserSchemaUpdate(BaseModel):
    """
    The application's view of users. This is how the API represents users (as opposed to how the database represents them).
    """
    name: Optional[str] = None 
    email: Optional[str] = None 
    password: Optional[str] = None 
    new_password: Optional[str] = None 
    tier: Optional[int] = None 

    @field_validator('name', 'email', 'password', 'new_password')
    @classmethod
    def no_empty_strings(cls, v):
        if v is not None:
            stripped = v.strip()
            if stripped == "":
                raise ValueError("Fields cannot be empty or whitespace")
            return stripped
        return v
    
    @field_validator('tier')
    @classmethod
    def valid_tier(cls, v):
        if v is not None and v < 1:
            raise ValueError("Tier must be at least 1")
        return v

class UserSchemaReturn(BaseModel):
    """
    The application's view of users. This is how the API represents users (as opposed to how the database represents them).
    """
    name: str
    id: int
    email: str
    tier: int

    @classmethod
    def from_db_model(cls, user: User) -> "UserSchemaReturn":
        """Create a UserSchema from a User"""
        return cls(name=user.name, id=user.id, email=user.email, tier=user.tier)
    