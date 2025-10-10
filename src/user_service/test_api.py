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

# def created_users(session):
#     user_data1 = {"name": "foob", "id": 2, "email": "foob@gmail.com", "password": "fooby"}
#     user_data2 = {"name": "foog", "id": 3, "email": "foog@gmail.com", "password": "foogy"}
#     user_data3 = {"name": "foop", "id": 4, "email": "foop@gmail.com", "password": "foopy"}
#     try:
#         for user_data0 in [user_data1, user_data2, user_data3]:
#             session.execute(text("INSERT INTO users (name, id, email, password) " \
#             "VALUES (:name, :id, :email, :password)"), user_data0)
#         session.commit()
#     except IntegrityError as e:
#         print("IntegrityError:", e)
#         session.rollback()
#     except OperationalError as e:
#         print("OperationalError:", e)
#         session.rollback()
#     except SQLAlchemyError as e:
#         print("SqlAlchemyError:", e)
#         session.rollback()
#     return user_data1, user_data2, user_data3

@pytest.fixture(scope='function')
def created_user2(session):
    user_data2 = {"name": "foob", "id": 2, "email": "foob@gmail.com", "password": "fooby"}
    try:
        session.execute(text("INSERT INTO users (name, id, email, password) VALUES (:name, :id, :email, :password)"), user_data2)
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
    return user_data2

# def test_read_users(client, created_user):
#     extra_users = created_users
#     all_users = [created_user, extra_users]
#     response = client.get("/users/")
#     assert response.status_code == 200
#     assert response.json() == {
#         "user": all_users
#     }

def test_read_users(client, created_user, created_user2):
    users = [created_user, created_user2]
    response = client.get("/all_users/")
    # print(response.json())
    # print({'users': users})
    assert response.status_code == 200
    assert response.json() == {
        'users': users
    }

def test_read_user(client, created_user):
    response = client.get("/users/foo")
    assert response.status_code == 200
    assert response.json() == {
        "user": created_user
    }

def test_create_user(client):
    response = client.post(
        "/users/",
        json={"name": "bbb", "id": 100, "email": "bbb@gmail.com", "password": "bbb"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "user": {"name": "bbb", "id": 100, "email": "bbb@gmail.com", "password": "bbb"}
    }

def test_create_existing_user(client, created_user):
    response = client.post(
        "/users/",
        json=created_user,
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Item already exists"}

def test_empty_field(client, created_user):
    response = client.post(
        "/users/",
        json={"name": "sss", "id": "", "email": "", "password": ""}
    )
    assert response.status_code == 422

def test_nonexisting_user(client, created_user):
    response = client.get("/users/nonexistent")
    assert response.status_code == 200
