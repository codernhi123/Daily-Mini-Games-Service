import pytest
import time
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import Request
from datetime import datetime, timedelta, timezone

from .api import app
from .models.rate_limiter import rate_limiter, RateLimiter, check_rate_limiter
import shared.database as database 

truth = True
lies = False

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.authenticated_windows.clear()
    rate_limiter.unauthenticated_windows.clear()
    yield
    rate_limiter.authenticated_windows.clear()
    rate_limiter.unauthenticated_windows.clear()

@pytest.fixture(autouse=True)
def cleanup_db_connections():
    yield
    
    if database._engine is not None:
        database._engine.dispose()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def client_selective_rate_limiting():
    async def selective_rate_limit(request: Request):
        if request.method == "POST" and (
            request.url.path in ["/v2/users/", "/v2/authentications/"] or request.url.path.startswith("/v2/users/")
            ):
            return
        return await check_rate_limiter(request)

    app.dependency_overrides[check_rate_limiter] = selective_rate_limit

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture
def client_no_rate_limiting():
    async def skip_rate_limit():
        pass

    app.dependency_overrides[check_rate_limiter] = skip_rate_limit

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

def test_rate_limiter_authenticated_tier_1():
    limiter = RateLimiter()

    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=1, tier=1) == lies

def test_rate_limiter_authenticated_tier_3():
    limiter = RateLimiter()

    for i in range(6):
        assert limiter.check_authenticated_limit(id=1, tier=3) == truth
    assert limiter.check_authenticated_limit(id=1, tier=3) == lies

# @pytest.mark.skip(reason="Slower Test")
def test_rate_limiter_window_reset_authenticated():
    limiter = RateLimiter()

    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=1, tier=1) == lies

    time.sleep(10)
    assert limiter.check_authenticated_limit(id=1, tier=1) == truth

# @pytest.mark.skip(reason="Slower Test")
def test_rate_limiter_window_reset_unauthenticated():
    limiter = RateLimiter()

    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == truth
    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == lies

    time.sleep(10)
    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == truth

def test_rate_limiter_different_users_authenticated():
    limiter = RateLimiter()

    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=1, tier=1) == lies

    assert limiter.check_authenticated_limit(id=2, tier=1) == truth
    assert limiter.check_authenticated_limit(id=2, tier=1) == truth
    assert limiter.check_authenticated_limit(id=2, tier=1) == lies

def test_rate_limiter_unauthenticated():
    limiter = RateLimiter()

    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == truth
    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == lies

def test_rate_limiter_different_users_unauthenticated():
    limiter = RateLimiter()

    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == truth
    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == lies

    assert limiter.check_unauthenticated_limit(address="mystery_ip_456") == truth
    assert limiter.check_unauthenticated_limit(address="mystery_ip_456") == lies

# @pytest.mark.skip(reason="Slower Test")
def test_rate_limit_for_endpoint_unauthenticated(client):
    response = client.get("/v2/users/")
    assert response.status_code == 200

    response = client.get("/v2/users/")
    assert response.status_code == 429

    time.sleep(10)
    response = client.get("/v2/users/")
    assert response.status_code == 200

def test_rate_limiter_allows_requests(client_no_rate_limiting):
    with patch("user_service.models.rate_limiter.rate_limiter.check_unauthenticated_limit", return_value=True):
        response = client_no_rate_limiting.get("/v2/users/")
        assert response.status_code == 200

def test_rate_limiter_deny_requests(client):
    with patch("user_service.models.rate_limiter.rate_limiter.check_unauthenticated_limit", return_value=False):
        response = client.get("/v2/users/")
        assert response.status_code == 429

# @pytest.mark.skip(reason="Slower Test")
def test_rate_limiter_cleanup():
    limiter = RateLimiter()

    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=2, tier=1) == truth
    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == truth

    assert len(limiter.authenticated_windows) == 2
    assert len(limiter.unauthenticated_windows) == 1

    time.sleep(10)

    limiter.cleanup_windows()

    assert len(limiter.authenticated_windows) == 0
    assert len(limiter.unauthenticated_windows) == 0
    
def test_authenticated_user_tier_1(client_selective_rate_limiting):
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo", "id": 1000, "email": "foo@gmail.com", "password": "fooy", "tier": 1}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    )
    token = auth_response.json()["jwt"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 429
    client_selective_rate_limiting.post(
        "/v2/users/1000", json = {"password": "fooy"}
    )


def test_authenticated_user_tier_3(client_selective_rate_limiting):
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo2", "id": 2000, "email": "foo2@gmail.com", "password": "fooy", "tier": 3}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo2", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    )
    token = auth_response.json()["jwt"]
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(6):
        response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 429
    client_selective_rate_limiting.post(
        "/v2/users/2000", json = {"password": "fooy"}
    )


# @pytest.mark.skip(reason="Slower Test")
def test_revoked_jwt_user(client_selective_rate_limiting):
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo3", "id": 3000, "email": "foo3@gmail.com", "password": "fooy", "tier": 2}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo3", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    )
    token = auth_response.json()["jwt"]
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(4):
        response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200

    client_selective_rate_limiting.request(
        "DELETE",
        "/v2/authentications/",
        json=({"jwt": token}),
    )

    time.sleep(10)


    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 429
    client_selective_rate_limiting.post(
        "/v2/users/3000", json = {"password": "fooy"}
    )


def test_no_jwt_user(client):
    response = client.get("/v2/users/")
    assert response.status_code == 200

    response = client.get("/v2/users/")
    assert response.status_code == 429

def test_invalid_jwt_user(client):
    fake_headers = {"Authorization": "Bearer invalid.jwt.token"}

    response = client.get("/v2/users/", headers=fake_headers)
    assert response.status_code == 200

    response = client.get("/v2/users/", headers=fake_headers)
    assert response.status_code == 429


def test_expired_jwt_user(client_selective_rate_limiting):
    future = (datetime.now(timezone.utc) + timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S")

    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo4", "id": 4000, "email": "foo4@gmail.com", "password": "fooy", "tier": 2}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo4", "password": "fooy", "expiry": future}
    )
    token = auth_response.json()["jwt"]
    headers = {"Authorization": f"Bearer {token}"}

    time.sleep(3)
    
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 429
    client_selective_rate_limiting.post(
        "/v2/users/4000", json = {"password": "fooy"}
    )



def test_rate_limiter_different_users_authenticated_with_jwt(client_selective_rate_limiting):
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo5", "id": 5000, "email": "foo5@gmail.com", "password": "fooy", "tier": 1}
    )
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo6", "id": 6000, "email": "foo6@gmail.com", "password": "fooy", "tier": 1}
    )
    token_1 = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo5", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    ).json()["jwt"]
    token_2 = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo6", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    ).json()["jwt"]
    client_selective_rate_limiting.get("/v2/users/", headers={"Authorization": f"Bearer {token_1}"})
    client_selective_rate_limiting.get("/v2/users/", headers={"Authorization": f"Bearer {token_1}"})
    response_1 = client_selective_rate_limiting.get("/v2/users/", headers={"Authorization": f"Bearer {token_1}"})
    assert response_1.status_code == 429 

    response_2 = client_selective_rate_limiting.get("/v2/users/", headers={"Authorization": f"Bearer {token_2}"})
    assert response_2.status_code == 200 
    client_selective_rate_limiting.post(
        "/v2/users/5000", json = {"password": "fooy"}
    )
    client_selective_rate_limiting.post(
        "/v2/users/6000", json = {"password": "fooy"}
    )

# @pytest.mark.skip(reason="Slower Test")
def test_jwt_rate_limit_window_reset(client_selective_rate_limiting):
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo7", "id": 7000, "email": "foo7@gmail.com", "password": "fooy", "tier": 1}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo7", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    )
    token = auth_response.json()["jwt"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 429

    time.sleep(10)
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200
    client_selective_rate_limiting.post(
        "/v2/users/7000", json = {"password": "fooy"}
    )


def test_both_types_of_user_limits(client_selective_rate_limiting):
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo8", "id": 8000, "email": "foo8@gmail.com", "password": "fooy", "tier": 1}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo8", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    )
    token = auth_response.json()["jwt"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client_selective_rate_limiting.get("/v2/users/")
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/")
    assert response.status_code == 429

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 429
    client_selective_rate_limiting.post(
        "/v2/users/8000", json = {"password": "fooy"}
    )


def test_incomplete_authorization_header(client):
    response = client.get("/v2/users/", headers={"Authorization": "random token"})
    assert response.status_code == 200 

    response = client.get("/v2/users/", headers={"Authorization": "random token"})
    assert response.status_code == 429

def test_jwt_deleted_user(client_selective_rate_limiting):
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo9", "id": 9000, "email": "foo9@gmail.com", "password": "fooy", "tier": 1}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo9", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    )
    token = auth_response.json()["jwt"]
    headers = {"Authorization": f"Bearer {token}"}

    client_selective_rate_limiting.post(
        "/v2/users/9000", json = {"password": "fooy"}
    )
    rate_limiter.authenticated_windows.clear()
    rate_limiter.unauthenticated_windows.clear()

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers)
    assert response.status_code == 429

def test_different_tier_limits(client_selective_rate_limiting):
    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo10", "id": 10000, "email": "foo10@gmail.com", "password": "fooy", "tier": 1}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo10", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    )
    token_1 = auth_response.json()["jwt"]
    headers_1 = {"Authorization": f"Bearer {token_1}"}

    client_selective_rate_limiting.post(
        "/v2/users/",
        json={"name": "foo100", "id": 100000, "email": "foo100@gmail.com", "password": "fooy", "tier": 2}
    )
    auth_response = client_selective_rate_limiting.post(
        "/v2/authentications/",
        json={"name": "foo100", "password": "fooy", "expiry": "2026-12-31 23:59:59"}
    )
    token_2 = auth_response.json()["jwt"]
    headers_2 = {"Authorization": f"Bearer {token_2}"}

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers_1)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers_1)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers_1)
    assert response.status_code == 429

    response = client_selective_rate_limiting.get("/v2/users/", headers=headers_2)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers_2)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers_2)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers_2)
    assert response.status_code == 200
    response = client_selective_rate_limiting.get("/v2/users/", headers=headers_2)
    assert response.status_code == 429
    client_selective_rate_limiting.post(
        "/v2/users/10000", json = {"password": "fooy"}
    )
    client_selective_rate_limiting.post(
        "/v2/users/100000", json = {"password": "fooy"}
    )
    
