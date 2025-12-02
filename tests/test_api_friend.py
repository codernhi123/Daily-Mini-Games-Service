from datetime import datetime, timedelta, timezone
import pytest
#import time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from user_service.auth.jwt_helper import create_access_token
from user_service.models.rate_limiter import check_rate_limiter

from user_service.models.friend import FriendRepository, get_friend_repository
from user_service.models.user import Base, UserRepository, get_user_repository, password_hash

from user_service.api import app

@pytest.fixture(scope='function')
def user_repo(session):
    yield UserRepository(session)

@pytest.fixture(scope='function')
def friend_repo(session):
    yield FriendRepository(session)

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
def client(user_repo, friend_repo):
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_friend_repository] = lambda: friend_repo

    async def skip_rate_limit():
        pass

    app.dependency_overrides[check_rate_limiter] = skip_rate_limit

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture(scope='function')
def user_a_with_auth(session):
    plain_password = "password_a"
    hashed_password = password_hash(plain_password)
    user_data = {"name": "a", "id": 1, "email": "a@gmail.com", "password": hashed_password, "tier": 1}
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    token = create_access_token(
        user_id=user_data["id"], 
        expiry=expires
    )
    user_data["active_jwt"] = token
    try:
        session.execute(text("""INSERT INTO users (name, id, email, password, tier, active_jwt) VALUES (:name, :id, :email, :password, :tier, :active_jwt)"""), user_data)
        session.commit()
    except Exception as e:
        print(f"Error creating user in fixture: {e}")
        session.rollback()
        raise

    return {
        "user": {"name": "a", "id": 1, "email": "a@gmail.com", "tier": 1},
        "token": token
    }

@pytest.fixture(scope='function')
def user_b(session):
    # This fixture doesn't need a token, just inserts the user
    user_data = {"name": "b", "id": 2, "email": "b@gmail.com", "password": password_hash("pass_b"), "tier": 1}
    try:
        session.execute(
            text("INSERT INTO users (name, id, email, password, tier) VALUES (:name, :id, :email, :password, :tier)"),
            user_data
        )
        session.commit()
    except Exception:
        session.rollback()
    
    return user_data

@pytest.fixture(scope='function')
def user_b_with_auth(session):
    plain_password = "password_b"
    hashed_password = password_hash(plain_password)
    user_data = {"name": "b", "id": 2, "email": "b@gmail.com", "password": hashed_password, "tier": 1}
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    token = create_access_token(
        user_id=user_data["id"], 
        expiry=expires
    )
    user_data["active_jwt"] = token
    try:
        session.execute(text("""INSERT INTO users (name, id, email, password, tier, active_jwt) VALUES (:name, :id, :email, :password, :tier, :active_jwt)"""), user_data)
        session.commit()
    except Exception as e:
        print(f"Error creating user in fixture: {e}")
        session.rollback()
        raise

    return {
        "user": {"name": "b", "id": 2, "email": "b@gmail.com", "tier": 1},
        "token": token
    }

@pytest.fixture(scope='function')
def user_c_with_auth(session):
    plain_password = "password_c"
    hashed_password = password_hash(plain_password)
    user_data = {"name": "c", "id": 3, "email": "c@gmail.com", "password": hashed_password, "tier": 1}
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    token = create_access_token(
        user_id=user_data["id"], 
        expiry=expires
    )
    user_data["active_jwt"] = token
    try:
        session.execute(text("""INSERT INTO users (name, id, email, password, tier, active_jwt) VALUES (:name, :id, :email, :password, :tier, :active_jwt)"""), user_data)
        session.commit()
    except Exception as e:
        print(f"Error creating user in fixture: {e}")
        session.rollback()
        raise

    return {
        "user": {"name": "c", "id": 3, "email": "c@gmail.com", "tier": 1},
        "token": token
    }

def test_create_friend_request_a_to_b(client, user_a_with_auth, user_b):
    token_a = user_a_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b["id"]

    response_send = client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": f"{user_b_id}"}
    )
    assert response_send.status_code == 201
    assert response_send.json()["ok"] is True

def test_create_friend_request_a_to_a(client, user_a_with_auth):
    token_a = user_a_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]

    response_send = client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": f"{user_a_id}"}
    )
    assert response_send.status_code == 400
    assert response_send.json()["detail"] == "Cannot make friend with yourself"

def test_create_friend_request_a_to_b_with_wrong_auth(client, user_a_with_auth, user_b):
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b["id"]

    response_send = client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token=xxxxxxxx",
        json={"other": f"{user_b_id}"}
    )
    assert response_send.status_code == 401 #wrong auth error expected

def test_create_friend_request_duplicated(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": f"{user_b_id}"}
    )

    response_send = client.post(
        f"/v2/users/{user_b_id}/friend-requests/?token={token_b}",
        json={"other": f"{user_a_id}"}
    )
    assert response_send.status_code == 400
    assert response_send.json()["detail"] == "A pending request already exists between these users"

def test_update_nonexist_friend_request(client, user_a_with_auth, user_b_with_auth):
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]

    response_acp = client.put(
        f"/v2/users/{user_b_id}/friend-requests/{user_a_id}/?token={token_b}"
    )
    assert response_acp.status_code == 400
    assert response_acp.json()["detail"] == "No pending request to accept"

def test_b_list_friend_request(client, user_a_with_auth, user_b):
    token_a = user_a_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b["id"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )

    response_view_fr = client.get(
        f"/v2/users/{user_b_id}/friend-requests/?q=incoming"
    )
    data = response_view_fr.json()
    assert len(data) > 0

    request_data = data[0]
    assert response_view_fr.status_code == 200
    assert request_data["from"] == user_a_id
    assert request_data["to"] == user_b_id

def test_a_delete_friend_request_to_b(client, user_a_with_auth, user_b):
    token_a = user_a_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b["id"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )

    response_del = client.delete(
        f"/v2/users/{user_a_id}/friend-requests/{user_b_id}/?token={token_a}"
    )
    assert response_del.status_code == 200
    assert response_del.json()["ok"] is True

def test_delete_friend_nonexist_request(client, user_a_with_auth):
    token_a = user_a_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]

    response_del = client.delete(
        f"/v2/users/{user_a_id}/friend-requests/45/?token={token_a}"
    )
    assert response_del.status_code == 400
    assert response_del.json()["detail"] == "No request to cancel"

def test_b_accept_friend_request_from_a(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )

    response_acp = client.put(
        f"/v2/users/{user_b_id}/friend-requests/{user_a_id}/?token={token_b}"
    )
    assert response_acp.status_code == 200
    assert response_acp.json()["ok"] is True

def test_b_accept_nonexist_friend_request(client, user_b_with_auth):
    token_b = user_b_with_auth["token"]
    user_b_id = user_b_with_auth["user"]["id"]

    response_acp = client.put(
        f"/v2/users/{user_b_id}/friend-requests/45/?token={token_b}"
    )
    assert response_acp.status_code == 400
    assert response_acp.json()["detail"] == "No pending request to accept"

def test_accept_from_unrelated_user(client, user_a_with_auth, user_b_with_auth, user_c_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    user_c_id = user_c_with_auth["user"]["id"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )

    response_acp = client.put(
        f"/v2/users/{user_c_id}/friend-requests/{user_a_id}/?token={token_b}"
    )
    assert response_acp.status_code == 401

def test_send_friend_request_to_friends(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )
    client.put(
        f"/v2/users/{user_b_id}/friend-requests/{user_a_id}/?token={token_b}"
    )

    response_send = client.post(
        f"/v2/users/{user_b_id}/friend-requests/?token={token_b}",
        json={"other": f"{user_a_id}"}
    )
    assert response_send.status_code == 400
    assert response_send.json()["detail"] == "Already been friends"

def test_check_list_friends(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )
    client.put(
        f"/v2/users/{user_b_id}/friend-requests/{user_a_id}/?token={token_b}"
    )
    #test from a's view
    response_view_a = client.get(
        f"/v2/users/{user_a_id}/friends"
    )
    assert response_view_a.status_code == 200
    data_a = response_view_a.json()
    assert isinstance(data_a, list)
    assert len(data_a) == 1
    friend_of_a = data_a[0]
    assert friend_of_a == user_b_id

    #test from b's view
    response_view_b = client.get(
        f"/v2/users/{user_b_id}/friends"
    )
    assert response_view_b.status_code == 200
    data_b = response_view_b.json()
    assert isinstance(data_b, list)
    assert len(data_b) == 1
    friend_of_b = data_b[0]
    assert friend_of_b == user_a_id

def test_get_friend_by_id(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )
    client.put(
        f"/v2/users/{user_b_id}/friend-requests/{user_a_id}/?token={token_b}"
    )

    response = client.get(
        f"/v2/users/{user_b_id}/friends/{user_a_id}"
    )
    assert response.status_code == 200
    assert response.json() == f"You and user with ID: {user_a_id} are friends"

def test_get_friend_by_name(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    user_b_name = user_b_with_auth["user"]["name"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )
    client.put(
        f"/v2/users/{user_b_id}/friend-requests/{user_a_id}/?token={token_b}"
    )

    response = client.get(
        f"/v2/users/{user_a_id}/friends/{user_b_name}"
    )
    assert response.status_code == 200
    assert response.json() == f"You and {user_b_name} are friends"

def test_delete_friend_by_id(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    #user_b_name = user_b_with_auth["user"]["name"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )
    client.put(
        f"/v2/users/{user_b_id}/friend-requests/{user_a_id}/?token={token_b}"
    )

    response = client.delete(
        f"/v2/users/{user_a_id}/friends/{user_b_id}/?token={token_a}"
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

def test_delete_nonexist_friend_by_id(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    #user_b_name = user_b_with_auth["user"]["name"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )

    response = client.delete(
        f"/v2/users/{user_a_id}/friends/{user_b_id}/?token={token_a}"
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Friendship does not exist to be deleted"

def test_delete_friend_by_name(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    user_a_name = user_a_with_auth["user"]["name"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )
    client.put(
        f"/v2/users/{user_b_id}/friend-requests/{user_a_id}/?token={token_b}"
    )

    response = client.delete(
        f"/v2/users/{user_b_id}/friends/{user_a_name}/?token={token_b}"
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

def test_delete_nonexist_friend_by_name(client, user_a_with_auth, user_b_with_auth):
    token_a = user_a_with_auth["token"]
    token_b = user_b_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_b_id = user_b_with_auth["user"]["id"]
    user_a_name = user_a_with_auth["user"]["name"]
    client.post(
        f"/v2/users/{user_a_id}/friend-requests/?token={token_a}",
        json={"other": user_b_id}
    )

    response = client.delete(
        f"/v2/users/{user_b_id}/friends/{user_a_name}/?token={token_b}"
    )
    assert response.status_code == 400
    assert response.json()["detail"] == f"No friendship found between {user_b_id} and {user_a_name}"

def test_delete_friend_with_yourself_by_name(client, user_a_with_auth):
    token_a = user_a_with_auth["token"]
    user_a_id = user_a_with_auth["user"]["id"]
    user_a_name = user_a_with_auth["user"]["name"]

    response = client.delete(
        f"/v2/users/{user_a_id}/friends/{user_a_name}/?token={token_a}"
    )
    assert response.status_code == 400
    assert response.json()["detail"] == f"No friendship found between {user_a_id} and {user_a_name}"