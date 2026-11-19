"""YouTube (direct, own Google app): connect a channel, upload a video now or scheduled, read the history."""
import asyncio
import json
import secrets
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import youtube
from config import settings
from db import get_session
from models import FINAL, Publication
from routes.posts import ALLOWED, CHUNK, parse_schedule

router = APIRouter(prefix="/api/youtube")
PLATFORM = "youtube-direct"  # keeps these rows apart from the Zernio YouTube rows
MIN_AHEAD = 10 * 60
_states: set[str] = set()  # sign-in states we issued (guards the callback)


def _fail(e: youtube.YouTubeError):
    raise HTTPException(e.status, e.message)


@router.get("/status")
async def status():
    out = {"configured": youtube.configured(), "connected": youtube.connected(), "channel": None, "error": "",
           "redirect_uri": settings.youtube_redirect_uri}
    if out["connected"]:
        try:
            out["channel"] = await youtube.channel()
        except youtube.YouTubeError as e:
            out["error"], out["connected"] = e.message, youtube.connected()
    return out


@router.get("/connect")
async def connect():
    if not youtube.configured():
        raise HTTPException(400, "Put YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in backend/.env, then restart the backend.")
    state = secrets.token_urlsafe(16)
    _states.add(state)
    return {"url": youtube.auth_url(state)}


@router.get("/callback")
async def callback(code: str = "", state: str = "", error: str = ""):
    back = f"{settings.frontend_url}/#/youtube"
    if error or state not in _states or not code:
        return RedirectResponse(f"{back}?error={quote(error or 'The sign-in was cancelled or expired. Try again.')}")
    _states.discard(state)
    try:
        await youtube.exchange_code(code)
    except youtube.YouTubeError as e:
        return RedirectResponse(f"{back}?error={quote(e.message)}")
    return RedirectResponse(f"{back}?connected=1")


@router.post("/disconnect")
async def disconnect():
    youtube.disconnect()
    return {"ok": True}


async def _save_upload(file: UploadFile) -> tuple[str, int]:
    size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "v.mp4").suffix) as tmp:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > settings.max_video_mb * 1024 * 1024:
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(422, f"Video is over {settings.max_video_mb} MB")
            tmp.write(chunk)
    return tmp.name, size


def _tags(raw: str) -> list[str]:
    return [t.strip().lstrip("#") for t in raw.replace("\n", ",").split(",") if t.strip()][:15]


@router.post("/posts")
async def create(
    file: UploadFile = File(...), title: str = Form(...), description: str = Form(""), tags: str = Form(""),
    privacy: str = Form("public"), mode: str = Form("now"), scheduled_at: str = Form(""),
    tz: str = Form(settings.default_timezone), session: AsyncSession = Depends(get_session),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(422, "Only MP4 or MOV videos are accepted")
    if not title.strip():
        raise HTTPException(422, "YouTube needs a title")
    if len(title) > 100 or len(description) > 5000:
        raise HTTPException(422, "Title is over 100 characters or description over 5,000")
    if privacy not in ("public", "unlisted", "private"):
        raise HTTPException(422, "Visibility must be public, unlisted or private")
    when = None
    if mode == "schedule":
        when = parse_schedule(scheduled_at, tz)
        if when.timestamp() - time.time() < MIN_AHEAD:
            raise HTTPException(422, "Schedule at least 10 minutes from now.")
    path, size = await _save_upload(file)
    try:
        publish_at = when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if when else None
        vid = await youtube.upload(path, size, ALLOWED[ext], title.strip(), description, _tags(tags), privacy, publish_at)
        row = Publication(group_id=uuid.uuid4().hex[:12], filename=file.filename, title=title[:120], caption=description,
                          platform=PLATFORM, account_id="youtube", account_name="my channel", mode=mode,
                          scheduled_for=when.astimezone(timezone.utc) if when else None, timezone=tz,
                          visibility="public" if when else privacy, status="SCHEDULED" if when else "PUBLISHING",
                          zernio_post_id=vid, post_url=f"https://www.youtube.com/watch?v={vid}")  # column holds the video id
        session.add(row)
        await session.commit()
        return {"items": [row.as_dict()]}
    except youtube.YouTubeError as e:
        _fail(e)
    finally:
        Path(path).unlink(missing_ok=True)


async def _refresh(row: Publication):
    try:
        st = await youtube.video_state(row.zernio_post_id)
    except youtube.YouTubeError:
        return  # keep the last known status; the next refresh retries
    if st is None:
        row.status, row.error = "FAILED", "The video is no longer on YouTube."
        return
    row.status, row.error = youtube.map_state(st, row.visibility)


@router.get("/posts")
async def history(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Publication).where(Publication.platform == PLATFORM)
                                  .order_by(Publication.id.desc()).limit(100))).all()
    if youtube.connected():
        await asyncio.gather(*(_refresh(r) for r in rows if r.status not in FINAL and r.zernio_post_id))
        await session.commit()
    return {"items": [r.as_dict() for r in rows]}
