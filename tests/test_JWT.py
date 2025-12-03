from datetime import datetime, timedelta, timezone
import pytest
import os

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from user_service.auth.jwt_helper import create_access_token, validate_jwt
from user_service.models.rate_limiter import check_rate_limiter

from user_service.models.user import Base, UserRepository, get_user_repository, password_verification

from user_service.api import app

@pytest.fixture(scope='function')
def repo(session):
    yield UserRepository(session)

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
def client(repo):
    app.dependency_overrides[get_user_repository] = lambda: repo

    async def skip_rate_limit():
        pass

    app.dependency_overrides[check_rate_limiter] = skip_rate_limit

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

def test_get_authenticated(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )

    assert response2.status_code == 200
    data = response2.json()
    token = data["jwt"]
    payload = validate_jwt(token)
    user_id = int(payload.get("sub"))
    expiry_time = int(payload.get("exp"))
    expiry_dt = datetime.fromtimestamp(expiry_time, tz=timezone.utc)

    #30 seconds of leeway for expiry time check
    jwt_cookie = response2.cookies.get("jwt")
    assert jwt_cookie is not None
    assert abs((expiry_dt - want_fifty_mins_token).total_seconds()) < 30
    assert user_id == 3

def test_get_authenticated_not_future(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    ten_minutes_past_token = datetime.now(timezone.utc) - timedelta(minutes=10)
    ten_minutes_past_token_str = ten_minutes_past_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": ten_minutes_past_token_str}
    )

    assert response2.status_code == 400
    assert response2.json() == {"detail": "Expiry must be in the future, time is calculated based on UTC time."}

def test_get_authenticated_bad_format(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": "23"}
    )

    assert response2.status_code == 400
    assert response2.json() == {"detail": "Expiry must be in 'YYYY-MM-DD HH:MM:SS' format in UTC Time"}

def test_delete_authentication(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )
    assert response2.status_code == 200
    data = response2.json()
    token = data["jwt"]

    response3 = client.request(
        "DELETE",
        "/v2/authentications/",
        json={"jwt": token}
    )

    assert response3.status_code == 200
    assert response3.json() == {"detail": "JWT successfully revoked"}

def test_delete_authentication_expired_token(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )
    assert response2.status_code == 200

    expired_fifty_token = datetime.now(timezone.utc) - timedelta(minutes=50)
    expired = create_access_token(3, expired_fifty_token)
    response3 = client.request(
        "DELETE",
        "/v2/authentications/",
        json={"jwt": expired}
    )

    assert response3.status_code == 401
    assert response3.json() == {"detail": "Invalid or expired JWT"}

def test_update_user_JWT_token_update_nonpassword(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )
    assert response2.status_code == 200
    data = response2.json()
    token = data["jwt"]

    response3 = client.put("/v2/users/3", json={"name": "newfoo", "email": "newfoo@gmail.com", "tier": 2, "active_jwt": token})
    assert response3.status_code == 200 
    assert response3.json() == {
        "user": {"name": "newfoo", "id": 3, "email": "newfoo@gmail.com", "tier": 2}
    }

    verify= client.get("/v2/users/newfoo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "newfoo"
    assert verify.json()["user"]["id"] == 3
    assert verify.json()["user"]["email"] == "newfoo@gmail.com"
    assert verify.json()["user"]["tier"] == 2

    

def test_update_user_JWT_token_update_password(client,session):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )
    assert response2.status_code == 200
    data = response2.json()
    token = data["jwt"]
    
    response3 = client.put("/v2/users/3", json={"new_password": "newfooy", "active_jwt": token})
    assert response3.status_code == 200 
    assert response3.json() == {
        "user": {"name": "bbb", "id": 3, "email": "bbb@gmail.com", "tier": 3}
    }

    result = session.execute(text("SELECT password FROM users WHERE id = '3'"))
    new_password = result.scalar()
    assert password_verification("newfooy", new_password) is True
    assert password_verification("bbb", new_password) is False

def test_update_user_JWT_token_update_everything(client,session):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )
    assert response2.status_code == 200
    data = response2.json()
    token = data["jwt"]

    response3 = client.put("/v2/users/3", json={"name": "newfoo", "email": "newfoo@gmail.com", "new_password": "newfooy", "tier": 2, "active_jwt": token})
    assert response3.status_code == 200 
    assert response3.json() == {
        "user": {"name": "newfoo", "id": 3, "email": "newfoo@gmail.com", "tier": 2}
    }

    verify= client.get("/v2/users/newfoo")
    assert verify.status_code == 200
    assert verify.json()["user"]["name"] == "newfoo"
    assert verify.json()["user"]["id"] == 3
    assert verify.json()["user"]["email"] == "newfoo@gmail.com"
    assert verify.json()["user"]["tier"] == 2

    result = session.execute(text("SELECT password FROM users WHERE id = '3'"))
    new_password = result.scalar()
    assert password_verification("newfooy", new_password) is True
    assert password_verification("bbb", new_password) is False

def test_update_user_JWT_token_expired_token(client,session):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )
    assert response2.status_code == 200

    expired_fifty_token = datetime.now(timezone.utc) - timedelta(minutes=50)
    expired_token = create_access_token(3, expired_fifty_token)

    response3 = client.put("/v2/users/3", json={"name": "newfoo", "email": "newfoo@gmail.com", "new_password": "newfooy", "tier": 2, "active_jwt": expired_token})
    assert response3.status_code == 401 
    assert response3.json() == {"detail": "Invalid or expired JWT"}

def test_update_user_JWT_token_wrong_id_token(client,session):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )
    assert response2.status_code == 200

    wrong_id_token = create_access_token(100, want_fifty_mins_token)

    response3 = client.put("/v2/users/3", json={"name": "newfoo", "email": "newfoo@gmail.com", "new_password": "newfooy", "tier": 2, "active_jwt": wrong_id_token})
    assert response3.status_code == 401 
    assert response3.json() == {"detail": "JWT does not match user"}

def test_get_authenticated_bad_username(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    ten_minutes_past_token = datetime.now(timezone.utc) - timedelta(minutes=10)
    ten_minutes_past_token_str = ten_minutes_past_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "BADUSERNAME", "password": "bbb", "expiry": ten_minutes_past_token_str}
    )

    assert response2.status_code == 401
    assert response2.json() == {"detail": "Invalid credentials"}

def test_get_authenticated_bad_password(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    ten_minutes_past_token = datetime.now(timezone.utc) - timedelta(minutes=10)
    ten_minutes_past_token_str = ten_minutes_past_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "BADPASSWORD", "expiry": ten_minutes_past_token_str}
    )

    assert response2.status_code == 401
    assert response2.json() == {"detail": "Invalid credentials"}

def test_logout_endpoint(client):
    response = client.post(
        "/v2/users/",
        json={"name": "bbb", "id": 3, "email": "bbb@gmail.com", "password": "bbb", "tier": 3}
    )
    assert response.status_code == 201

    want_fifty_mins_token = datetime.now(timezone.utc) + timedelta(minutes=50)
    want_fifty_mins_token_str = want_fifty_mins_token.strftime("%Y-%m-%d %H:%M:%S")

    response2 = client.post(
        "/v2/authentications/",
        json={"name": "bbb", "password": "bbb", "expiry": want_fifty_mins_token_str}
    )

    assert response2.status_code == 200
    data = response2.json()
    token = data["jwt"]
    payload = validate_jwt(token)
    user_id = int(payload.get("sub"))
    expiry_time = int(payload.get("exp"))
    expiry_dt = datetime.fromtimestamp(expiry_time, tz=timezone.utc)

    jwt_cookie = response2.cookies.get("jwt")
    assert jwt_cookie is not None

    #30 seconds of leeway for expiry time check
    assert abs((expiry_dt - want_fifty_mins_token).total_seconds()) < 30
    assert user_id == 3

    response3 = client.post("/v2/authentications/logout")

    assert response3.status_code == 200
    assert response3.json() == {"message": "Logged out"}

    set_cookie = response3.headers.get("set-cookie")
    assert set_cookie is not None

    assert client.cookies.get("jwt") is None
    assert "jwt=" in set_cookie
    assert "Max-Age=0" in set_cookie or "Expires=" in set_cookie
    assert "Path=/" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=None" in set_cookie
    assert "Secure" in set_cookie  

def test_go_to_frontend_redirect(client):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    response = client.get("/go-to-frontend", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == frontend_url
