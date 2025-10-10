import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy import create_engine, text

from .models.user import Base, User, UserRepository, get_user_repository

from .api import app

@pytest.fixture(scope='function')
def engine():
    engine = create_engine("sqlite:///:memory:?check_same_thread=False")
    Base.metadata.create_all(bind=engine)
    yield engine

@pytest.fixture(scope='function')
def session(engine):
    conn = engine.connect()
    conn.begin()
    db = Session(bind=conn)
    yield db
    db.rollback()
    conn.close()

@pytest.fixture(scope='function')
def repo(session):
    yield UserRepository(session)

@pytest.fixture(scope='function')
def client(repo):
    app.dependency_overrides[get_user_repository] = lambda: repo
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope='function')
def created_user(session):
    user_data = {"name": "foo", "id": 1, "email": "foo@gmail.com", "password": "fooy"}
    try:
        session.execute(text("INSERT INTO users (name, id, email, password) VALUES (:name, :id, :email, :password)"), user_data)
        session.commit()
    except IntegrityError as e:
        print("IntegrityError:", e)
        session.rollback()
    except OperationalError as e:
        print("OperationalError:", e)
        session.rollback()
    except SQLAlchemyError as e:
        print("SqlAlchemyError:", e)
        session.rollback()
    return user_data

def test_read_user(client, created_user):
    response = client.get("/users/foo")
    assert response.status_code == 200
    assert response.json() == {
        "user": created_user
    }

def test_create_user(client):
    response = client.post(
        "/users/",
        json={"name": "ppp", "id": 100, "email": "ppp@gmail.com", "password": "ppp"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "user": {"name": "ppp", "id": 100, "email": "ppp@gmail.com", "password": "ppp"}
    }

def test_create_existing_user(client, created_user):
    response = client.post(
        "/users/",
        json=created_user,
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Item already exists"}

