from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import io

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy.orm import Session

from .user import User
from shared.database import get_db

router = APIRouter(prefix="/v2", tags=["avatar"])

AVATAR_DIR = Path("/tmp/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
MAX_SIDE = 256
MAX_BYTES = 10 * 1024 * 1024  # 10MB limit


def _avatar_path(user_id: int) -> Path:
    return AVATAR_DIR / f"{user_id}.png"


def _process_image_to_png(data: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGBA")
            w, h = im.size
            # center crop to square
            if w != h:
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                im = im.crop((left, top, left + side, top + side))
            if im.size[0] > MAX_SIDE:
                im = im.resize((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            im.save(out, format="PNG", optimize=True)
            return out.getvalue()
    except Exception:
        raise HTTPException(status_code=400, detail="Unsupported or corrupted image")


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/avatar", status_code=201)
@router.put("/users/{user_id}/avatar", status_code=200)
async def upload_avatar(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="No file uploaded")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large")
    processed = _process_image_to_png(raw)
    _avatar_path(user_id).write_bytes(processed)

    user.has_avatar = True
    user.avatar_updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"user_id": user_id, "detail": "Avatar uploaded successfully"}


@router.get("/users/{user_id}/avatar")
async def get_avatar(user_id: int, db: Session = Depends(get_db)):
    _get_user_or_404(db, user_id)
    path = _avatar_path(user_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="No avatar for this user")
    return FileResponse(path, media_type="image/png")


@router.delete("/users/{user_id}/avatar")
async def delete_avatar(user_id: int, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    path = _avatar_path(user_id)
    if path.exists():
        path.unlink()
    user.has_avatar = False
    user.avatar_updated_at = None
    db.commit()
    return {"user_id": user_id, "detail": "Avatar deleted successfully"}

