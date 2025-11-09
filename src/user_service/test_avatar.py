# tests/test_avatar.py
import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from user_service.api import app
from user_service.test_rate_limiter import check_rate_limiter


# --------- fixtures (mirror your other tests) ---------

@pytest.fixture(scope="function")
def client_no_rate_limiting():
    async def skip_rate_limit():
        # override to bypass rate limiting for these tests
        pass

    app.dependency_overrides[check_rate_limiter] = skip_rate_limit
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

    


# --------- helpers ---------

def make_png_bytes(side=300, color=(20, 120, 220)):
    """Create an in-memory PNG. side>256 ensures server downscales."""
    img = Image.new("RGB", (side, side), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def non_image_bytes(n=1024):
    return b"x" * n


# --------- tests ---------

def test_avatar_full_flow_post_get_delete(client_no_rate_limiting):
    # create user (status 201)
    r = client_no_rate_limiting.post(
        "/v2/users/",
        json={"name": "ava", "id": 101, "email": "ava@example.com", "password": "pw", "tier": 1},
    )
    assert r.status_code == 201

    # POST first upload -> 201
    files = {"file": ("pic.png", make_png_bytes(512), "image/png")}
    r = client_no_rate_limiting.post("/v2/users/101/avatar", files=files)
    assert r.status_code == 201
    assert r.json()["detail"].lower().startswith("avatar")

    # GET -> 200 and image/png
    r = client_no_rate_limiting.get("/v2/users/101/avatar")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 0

    # DELETE -> 200
    r = client_no_rate_limiting.delete("/v2/users/101/avatar")
    assert r.status_code == 200
    assert r.json()["detail"].lower().startswith("avatar deleted")

    # GET after delete -> 404
    r = client_no_rate_limiting.get("/v2/users/101/avatar")
    assert r.status_code == 404
    assert r.json()["detail"] == "No avatar for this user"
    
    response = client_no_rate_limiting.post("/v2/users/101", json = {"password": "pw"})
    assert response.status_code == 200
    assert response.json() == {"message": f"User '{101}' deleted successfully."}

def test_put_updates_existing_avatar(client_no_rate_limiting):
    client_no_rate_limiting.post(
        "/v2/users/",
        json={"name": "bob", "id": 102, "email": "bob@example.com", "password": "pw", "tier": 2},
    )
    client_no_rate_limiting.post(
        "/v2/users/102/avatar",
        files={"file": ("a.png", make_png_bytes(400), "image/png")},
    )

    # PUT -> 200
    r = client_no_rate_limiting.put(
        "/v2/users/102/avatar",
        files={"file": ("b.png", make_png_bytes(300, (200, 40, 40)), "image/png")},
    )
    assert r.status_code == 200
    assert r.json()["detail"].lower().startswith("avatar uploaded")

    response = client_no_rate_limiting.post("/v2/users/102", json = {"password": "pw"})
    assert response.status_code == 200
    assert response.json() == {"message": f"User '{102}' deleted successfully."}


def test_upload_for_unknown_user_is_404(client_no_rate_limiting):
    r = client_no_rate_limiting.post(
        "/v2/users/9999/avatar",
        files={"file": ("x.png", make_png_bytes(300), "image/png")},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


def test_post_413_when_image_too_large(client_no_rate_limiting):
    client_no_rate_limiting.post(
        "/v2/users/",
        json={"name": "big", "id": 103, "email": "big@example.com", "password": "pw", "tier": 1},
    )

    # Create a PNG, then pad to exceed 10MB limit used by the router
    buf = io.BytesIO()
    Image.new("RGB", (6000, 6000), (0, 0, 0)).save(buf, format="PNG")
    data = buf.getvalue()
    if len(data) <= 10 * 1024 * 1024:
        data += b"0" * (10 * 1024 * 1024 - len(data) + 1)

    r = client_no_rate_limiting.post(
        "/v2/users/103/avatar",
        files={"file": ("huge.png", data, "image/png")},
    )
    assert r.status_code == 413
    assert r.json()["detail"] == "Image too large"

    response = client_no_rate_limiting.post("/v2/users/103", json = {"password": "pw"})
    assert response.status_code == 200
    assert response.json() == {"message": f"User '{103}' deleted successfully."}


def test_post_400_when_not_an_image(client_no_rate_limiting):
    client_no_rate_limiting.post(
        "/v2/users/",
        json={"name": "bad", "id": 104, "email": "bad@example.com", "password": "pw", "tier": 1},
    )
    r = client_no_rate_limiting.post(
        "/v2/users/104/avatar",
        files={"file": ("junk.bin", non_image_bytes(), "application/octet-stream")},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Unsupported or corrupted image"

    response = client_no_rate_limiting.post("/v2/users/104", json = {"password": "pw"})
    assert response.status_code == 200
    assert response.json() == {"message": f"User '{104}' deleted successfully."}


def test_post_422_when_missing_file(client_no_rate_limiting):
    client_no_rate_limiting.post(
        "/v2/users/",
        json={"name": "nofile", "id": 105, "email": "nofile@example.com", "password": "pw", "tier": 1},
    )
    r = client_no_rate_limiting.post("/v2/users/105/avatar", files={})
    assert r.status_code == 422

    response = client_no_rate_limiting.post("/v2/users/105", json = {"password": "pw"})
    assert response.status_code == 200
    assert response.json() == {"message": f"User '{105}' deleted successfully."}

