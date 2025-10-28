import pytest
import time
from unittest.mock import patch
from fastapi.testclient import TestClient

from .api import app
from .models.rate_limiter import rate_limiter, RateLimiter, check_rate_limiter

truth = True
lies = False

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.authenticated_windows.clear()
    rate_limiter.authenticated_windows.clear()
    yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

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

@pytest.mark.skip(reason="Slower Test")
def test_rate_limiter_window_reset_authenticated():
    limiter = RateLimiter()

    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=1, tier=1) == lies

    time.sleep(10.1)
    assert limiter.check_authenticated_limit(id=1, tier=1) == truth

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

@pytest.mark.skip(reason="Slower Test")
def test_rate_limit_for_endpoint_unauthenticated(client):
    response = client.get("/v2/all_users/")
    assert response.status_code == 200

    response = client.get("/v2/all_users/")
    assert response.status_code == 429

    time.sleep(10.1)
    response = client.get("/v2/all_users/")
    assert response.status_code == 200

@pytest.mark.skip(reason="Needs JWT")
def test_rate_limit_for_endpoint_authenticated(client_no_rate_limiting):
    pass

def test_rate_limiter_allows_requests(client_no_rate_limiting):
    with patch("user_service.models.rate_limiter.rate_limiter.check_unauthenticated_limit", return_value=True):
        response = client_no_rate_limiting.get("/v2/all_users/")
        assert response.status_code == 200

def test_rate_limiter_deny_requests(client):
    with patch("user_service.models.rate_limiter.rate_limiter.check_unauthenticated_limit", return_value=False):
        response = client.get("/v2/all_users/")
        assert response.status_code == 429

@pytest.mark.skip(reason="Slower Test")
def test_rate_limiter_cleanup():
    limiter = RateLimiter()

    assert limiter.check_authenticated_limit(id=1, tier=1) == truth
    assert limiter.check_authenticated_limit(id=2, tier=1) == truth
    assert limiter.check_unauthenticated_limit(address="mystery_ip_123") == truth

    assert len(limiter.authenticated_windows) == 2
    assert len(limiter.unauthenticated_windows) == 1

    time.sleep(10.1)

    limiter.cleanup_windows()

    assert len(limiter.authenticated_windows) == 0
    assert len(limiter.unauthenticated_windows) == 0
    