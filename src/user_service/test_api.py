import pytest
#import time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy import create_engine, text
from .models.rate_limiter import check_rate_limiter

from .models.user import Base, UserRepository, get_user_repository, password_hash, password_verification

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

    async def skip_rate_limit():
        pass

    app.dependency_overrides[check_rate_limiter] = skip_rate_limit

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture(scope='function')
def created_user(session):
    hashed_password = password_hash("fooy")
    user_data = {"name": "foo", "id": 1, "email": "foo@gmail.com", "password": hashed_password, "tier": 1}
    try:
        session.execute(text("INSERT INTO users (name, id, email, password, tier) VALUES (:name, :id, :email, :password, :tier)"), user_data)
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
    return {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}

@pytest.fixture(scope='function')
def created_user2(session):
    hashed_password = password_hash("fooby")
    user_data2 = {"name": "foob", "id": 2, "email": "foob@gmail.com", "password": hashed_password, "tier": 2}
    try:
        session.execute(text("INSERT INTO users (name, id, email, password, tier) VALUES (:name, :id, :email, :password, :tier)"), user_data2)
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
    return {"name": "foob", "id": 2, "email": "foob@gmail.com", "tier": 2}

# @pytest.fixture(scope='function')
# def created_20000_users(client):
#     user = []
#     for i in range(20000):
#         client.post("/v2/users/", json = {"name": f"user{i}", "id": i, "email": f"user{i}@email.com", "password": f"password{i}"})
#         user.append({"name": f"user{i}", "id": i, "email": f"user{i}@email.com", "password": f"password{i}"})
#     return user

# def test_created_20000_users(client, created_20000_users):
#     start_time = time.time() 
#     response = client.get("/v2/users/user5000")
#     end_time = time.time()
#     time_elapsed = end_time - start_time
#     print(time_elapsed)
#     assert response.status_code == 200
#     assert response.json() == {"user": {"name": f"user5000", "id": 5000, "email": "user5000@email.com"}}
#     assert time_elapsed < 0.127
    
def test_read_users(client, created_user, created_user2):
    users = [created_user, created_user2]
    response = client.get("/v2/all_users/")
    assert response.status_code == 200
    assert response.json() == {
        'users': users
    }

def test_read_user(client, created_user):
    response = client.get("/v2/users/foo")
    assert response.status_code == 200
    assert response.json() == {
        "user": created_user
    }

def test_read_user_by_id(client, created_user):
    response = client.get("/v2/users_by_id/1")
    assert response.status_code == 200
    assert response.json() == {
        "user": created_user
    }

def test_create_user(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201
    assert response.json() == {
        "user": {"name": "bbb", "id": 3, "email": "bbb@gmail.com", "tier": 3}
    }

def test_create_user_default_tier(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "user": {"name": "bbb", "id": 3, "email": "bbb@gmail.com", "tier": 1}
    }

def test_create_user_invalid_tier(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": -1}
    )
    assert response.status_code == 422

def test_create_existing_user(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "foo", "id": 1, "email": "foo@gmail.com", "password": "fooy", "tier": 1},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Item already exists"}

def test_empty_string_fields(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "", "id": 2, "email": "", "password": "",  "tier": 1}
    )
    assert response.status_code == 422

def test_whitespace_string_fields(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "   ", "id": 2, "email": "   ", "password": "   ", "tier": 1}
    )
    assert response.status_code == 422

def test_empty_int_field(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "hi", "id": "", "email": "hi@gmail.com", "password": "hihi", "tier": 1}
    )
    assert response.status_code == 422

def test_whitespace_int_field(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "hi", "id": 2, "email": "hi@gmail.com", "password": "hihi", "tier": "   "}
    )
    assert response.status_code == 422

def test_empty_tier_field(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "hi", "id": 2, "email": "hi@gmail.com", "password": "hihi", "tier": ""}
    )
    assert response.status_code == 422

def test_whitespace_tier_field(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "hi", "id": "   ", "email": "hi@gmail.com", "password": "hihi", "tier": 1}
    )
    assert response.status_code == 422

def test_empty_fields(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "", "id": "", "email": "", "password": "", "tier": ""}
    )
    assert response.status_code == 422

def test_whitespace_fields(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": "   ", "id": "   ", "email": "   ", "password": "   ", "tier": "   "}
    )
    assert response.status_code == 422

def test_null_fields(client, created_user):
    response = client.post(
        "/v2/users/",
        json={"name": None, "id": None, "email": None, "password": None, "tier": None}
    )
    assert response.status_code == 422

def test_nonexisting_user(client, created_user):
    response = client.get("/v2/users/nonexistent")
    assert response.status_code == 404

def test_deleting_user(client):
    response = client.post(
        "/v2/users/",
        json={"name": "Jack", "id": 100, "email": "jack@gmail.com", "password": "jackjack", "tier": 1}
    )
    assert response.status_code == 201
    
    response = client.post("/v2/users/100", json = {"password": "jackjack"})
    assert response.status_code == 200
    assert response.json() == {"message": f"User '{100}' deleted successfully."}

def test_deleting_user_wrong_password(client):
    response = client.post(
        "/v2/users/",
        json={"name": "Jack", "id": 100, "email": "jack@gmail.com", "password": "jackjack", "tier": 1}
    )
    assert response.status_code == 201
    
    response = client.post("/v2/users/100", json = {"password": "jackjackjack"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid password for deletion"}

def test_deleting_user_null_password(client):
    response = client.post(
        "/v2/users/",
        json={"name": "Jack", "id": 100, "email": "jack@gmail.com", "password": "jackjack", "tier": 1}
    )
    assert response.status_code == 201
    
    response = client.post("/v2/users/100", json = {"password": None})
    assert response.status_code == 401

def test_deleting_user_whitespace_password(client):
    response = client.post(
        "/v2/users/",
        json={"name": "Jack", "id": 100, "email": "jack@gmail.com", "password": "jackjack", "tier": 1}
    )
    assert response.status_code == 201
    
    response = client.post("/v2/users/100", json = {"password": "   "})
    assert response.status_code == 422

def test_deleting_user_empty_password(client):
    response = client.post(
        "/v2/users/",
        json={"name": "Jack", "id": 100, "email": "jack@gmail.com", "password": "jackjack", "tier": 1}
    )
    assert response.status_code == 201
    
    response = client.post("/v2/users/100", json = {"password": ""})
    assert response.status_code == 422

def test_deleting_user_no_password(client):
    response = client.post(
        "/v2/users/",
        json={"name": "Jack", "id": 100, "email": "jack@gmail.com", "password": "jackjack", "tier": 1}
    )
    assert response.status_code == 201
    
    response = client.post("/v2/users/100")
    assert response.status_code == 422

def test_deleting_nonexixting_user(client):
    response = client.post("/v2/users/100", json = { "password": "jackjackjack"})
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

#testing the testing pipeline 

def test_password_hashing():
    regular_password = "mysecretpassword"
    hashed_password = password_hash(regular_password)
    hashed_password_2 = password_hash(regular_password)
    assert hashed_password != regular_password
    assert hashed_password.startswith("$2b$")
    assert len(hashed_password) == 60
    assert password_verification(regular_password, hashed_password) is True
    assert password_verification("myfakepassword", hashed_password) is False
    assert hashed_password != hashed_password_2 
    assert password_verification(regular_password, hashed_password_2) is True
    assert password_verification("myfakepassword", hashed_password_2) is False

def test_password_hashing_in_database(client, session):
    response = client.post(
        "/v2/users/",
        json={"name": "bbbb", "id": 4, "email": "bbbb@gmail.com", "password": "bbbb", "tier": 1}
    )
    assert response.status_code == 201
    result = session.execute(text("SELECT password FROM users WHERE name = 'bbbb'"))
    regular_password = "bbbb"
    password_stored = result.scalar()
    assert password_stored != "bbbb"
    assert password_stored.startswith("$2b$")
    assert len(password_stored) == 60
    assert password_verification(regular_password, password_stored) is True
    assert password_verification("myfakepassword", password_stored) is False

def test_update_user_name(client, created_user):
    response = client.put("/v2/users/1", json={"name": "newfoo", "password": "fooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "newfoo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }

def test_update_user_email(client, created_user):
    response = client.put("/v2/users/1", json={"email": "newfoo@gmail.com", "password": "fooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "newfoo@gmail.com", "tier": 1}
    }

def test_update_user_tier(client, created_user):
    response = client.put("/v2/users/1", json={"tier": 4, "password": "fooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 4}
    }

def test_update_user_name_and_email(client, created_user):
    response = client.put("/v2/users/1", json={"name": "newfoo", "email": "newfoo@gmail.com", "password": "fooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "newfoo", "id": 1, "email": "newfoo@gmail.com", "tier": 1}
    }

def test_update_all_user_info(client, created_user):
    response = client.put("/v2/users/1", json={"name": "newfoo", "email": "newfoo@gmail.com", "password": "fooy", "tier": 4})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "newfoo", "id": 1, "email": "newfoo@gmail.com", "tier": 4}
    }

def test_update_user_password(client, created_user, session):
    response = client.put("/v2/users/1", json={"password": "fooy", "new_password": "newfooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    new_password = result.scalar()
    assert password_verification("newfooy", new_password) is True
    assert password_verification("fooy", new_password) is False

def test_wrong_user_password(client, created_user):
    response = client.put("/v2/users/1", json={"name": "newfoo", "email": "newfoo@gmail.com", "password": "wrongfooy"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid password for update"}

def test_no_user_password_no_JWT(client, created_user):
    response = client.put("/users/1", json={"name": "newfoo", "email": "newfoo@gmail.com"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Password or JWT required"}

def test_updating_nonexisting_user(client, created_user):
    response = client.put("/v2/users/3", json={"name": "newfoo", "email": "newfoo@gmail.com", "password": "fooy"})
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

def test_wrong_user_password_for_update(client, created_user):
    response = client.put("/v2/users/1", json={"name": "newfoo", "email": "newfoo@gmail.com", "password": "wrongfooy", "new_password": "newfooy"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid password for update"}

def test_duplicate_name(client, created_user, created_user2):
    response = client.put("/v2/users/1", json={"name": "foob", "password": "fooy"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Name already exists"}

def test_duplicate_email(client, created_user, created_user2):
    response = client.put("/v2/users/1", json={"email": "foob@gmail.com", "password": "fooy"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already exists"}

def test_duplicate_password(client, created_user, created_user2, session):
    response = client.put("/v2/users/1", json={"password": "fooy", "new_password": "fooby"})
    assert response.status_code == 200
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    new_password = result.scalar()
    assert password_verification("fooby", new_password) is True
    assert password_verification("fooy", new_password) is False

def test_update_user_with_different_user_password(client, created_user, created_user2):
    response = client.put("/v2/users/1", json={"name": "newfoo", "email": "newfoo@gmail.com", "password": "fooby"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid password for update"}

    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"

def test_update_password_multiple_times(client, created_user, session):
    response = client.put("/v2/users/1", json={"password": "fooy", "new_password": "newfooy1"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    new_password = result.scalar()
    assert password_verification("newfooy1", new_password) is True
    assert password_verification("fooy", new_password) is False

    response2 = client.put("/v2/users/1", json={"password": "newfooy1", "new_password": "newfooy2"})
    assert response2.status_code == 200
    assert response2.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    new_password = result.scalar()
    assert password_verification("newfooy2", new_password) is True
    assert password_verification("newfooy1", new_password) is False

def test_update_password_secure(client, created_user, session):
    response = client.put("/v2/users/1", json={"password": "fooy", "new_password": "newfooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    new_password = result.scalar()
    assert new_password != "newfooy"
    assert new_password.startswith("$2b$")
    assert len(new_password) == 60
    assert password_verification("newfooy", new_password) is True
    assert password_verification("fooy", new_password) is False

def test_update_password_with_different_user_password(client, created_user, created_user2, session):
    response = client.put("/v2/users/1", json={"password": "fooby", "new_password": "newfooy"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid password for update"}
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    original_password = result.scalar()
    assert password_verification("fooy", original_password) is True
    assert password_verification("newfooy", original_password) is False

def test_update_same_name(client, created_user):
    response = client.put("/v2/users/1", json={"name": "foo", "password": "fooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }

def test_update_same_email(client, created_user):
    response = client.put("/v2/users/1", json={"email": "foo@gmail.com", "password": "fooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }

def test_update_same_tier(client, created_user):
    response = client.put("/v2/users/1", json={"tier": 1, "password": "fooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }

def test_update_same_name_and_email(client, created_user):
    response = client.put("/v2/users/1", json={"name": "foo", "email": "foo@gmail.com", "password": "fooy"})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }

def test_update_same_info(client, created_user):
    response = client.put("/v2/users/1", json={"name": "foo", "email": "foo@gmail.com", "password": "fooy", "tier": 1})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }

def test_update_same_password(client, created_user, session):
    response = client.put("/v2/users/1", json={"password": "fooy", "new_password": "fooy"})
    assert response.status_code == 200
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    original_password = result.scalar()
    assert password_verification("fooy", original_password) is True

def test_update_null_name(client, created_user):
    response = client.put("/v2/users/1", json={"name": None, "email": "fooy@gmail.com", "password": "fooy", "tier": 2})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "fooy@gmail.com", "tier": 2}
    }

def test_update_null_email(client, created_user):
    response = client.put("/v2/users/1", json={"name": "fooy", "email": None, "password": "fooy", "tier": 2})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "fooy", "id": 1, "email": "foo@gmail.com", "tier": 2}
    }

def test_update_null_tier(client, created_user):
    response = client.put("/v2/users/1", json={"name": "fooy", "email": "fooy@gmail.com", "password": "fooy", "tier": None})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "fooy", "id": 1, "email": "fooy@gmail.com", "tier": 1}
    }

def test_update_null_name_and_email(client, created_user):
    response = client.put("/v2/users/1", json={"name": None, "email": None, "password": "fooy", "tier": 2})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 2}
    }

def test_update_null_info(client, created_user):
    response = client.put("/v2/users/1", json={"name": None, "email": None, "password": "fooy", "tier": None})
    assert response.status_code == 200
    assert response.json() == {
        "user": {"name": "foo", "id": 1, "email": "foo@gmail.com", "tier": 1}
    }

def test_update_null_new_password(client, created_user, session):
    response = client.put("/v2/users/1", json={"password": "fooy", "new_password": None})
    assert response.status_code == 200
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    original_password = result.scalar()
    assert password_verification("fooy", original_password) is True

def test_update_empty_name(client, created_user):
    response = client.put("/v2/users/1", json={"name": "", "email": "fooy@gmail.com", "password": "fooy", "tier": 2})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_empty_email(client, created_user):
    response = client.put("/v2/users/1", json={"name": "fooy", "email": "", "password": "fooy", "tier": 2})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_empty_tier(client, created_user):
    response = client.put("/v2/users/1", json={"name": "fooy", "email": "fooy@gmail.com", "password": "fooy", "tier": ""})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_empty_name_and_email(client, created_user):
    response = client.put("/v2/users/1", json={"name": "", "email": "", "password": "fooy", "tier": 2})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_empty_info(client, created_user):
    response = client.put("/v2/users/1", json={"name": "", "email": "", "password": "fooy", "tier": ""})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_empty_new_password(client, created_user, session):
    response = client.put("/v2/users/1", json={"password": "fooy", "new_password": ""})
    assert response.status_code == 422
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    original_password = result.scalar()
    assert password_verification("fooy", original_password) is True

    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_empty_user_password(client, created_user):
    response = client.put("/v2/users/1", json={"name": "fooy", "email": "fooy@gmail.com", "password": "", "tier": 2})
    assert response.status_code == 422

    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_whitespace_name(client, created_user):
    response = client.put("/v2/users/1", json={"name": "   ", "email": "fooy@gmail.com", "password": "fooy", "tier": 2})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_whitespace_email(client, created_user):
    response = client.put("/v2/users/1", json={"name": "fooy", "email": "   ", "password": "fooy", "tier": 2})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_whitespace_tier(client, created_user):
    response = client.put("/v2/users/1", json={"name": "fooy", "email": "fooy@gmail.com", "password": "fooy", "tier": ""})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_whitespace_name_and_email(client, created_user):
    response = client.put("/v2/users/1", json={"name": "   ", "email": "   ", "password": "fooy", "tier": 2})
    assert response.status_code == 422
    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_update_whitespace_new_password(client, created_user, session):
    response = client.put("/v2/users/1", json={"password": "fooy", "new_password": "   "})
    assert response.status_code == 422
    result = session.execute(text("SELECT password FROM users WHERE id = '1'"))
    original_password = result.scalar()
    assert password_verification("fooy", original_password) is True

    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

def test_whitespace_user_password(client, created_user):
    response = client.put("/v2/users/1", json={"name": "newfoo", "email": "newfoo@gmail.com", "password": "   "})
    assert response.status_code == 422

    verify= client.get("/v2/users/foo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "foo"
    assert verify.json()["user"]["email"] == "foo@gmail.com"
    assert verify.json()["user"]["tier"] == 1

