"""Upload a clip, publish now or at a chosen time, and read the history."""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import zernio
from config import settings
from db import get_session
from models import FINAL, Publication
from status import apply_post, map_status

router = APIRouter(prefix="/api")
ALLOWED = {".mp4": "video/mp4", ".mov": "video/quicktime"}
CHUNK = 1024 * 1024


def parse_schedule(local: str, tz: str) -> datetime:
    try:
        zone = ZoneInfo(tz)
        dt = datetime.fromisoformat(local).replace(tzinfo=zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "Invalid date, time or timezone")
    return dt


def check_copy(targets: list[dict], copy: dict) -> str | None:
    """Platform limits, checked before we spend time uploading."""
    for t in targets:
        c = copy.get(t["platform"], {})
        if t["platform"] == "instagram" and len(c.get("caption", "")) > 2200:
            return "Instagram caption is over 2,200 characters"
        if t["platform"] == "youtube":
            if not (c.get("title") or "").strip():
                return "YouTube needs a title"
            if len(c["title"]) > 100:
                return "YouTube title is over 100 characters"
            if len(c.get("caption", "")) > 5000:
                return "YouTube description is over 5,000 characters"
    return None


async def read_chunks(f: UploadFile):
    while chunk := await f.read(CHUNK):
        yield chunk


@router.post("/posts")
async def create(
    file: UploadFile = File(...), texts: str = Form("{}"), account_ids: list[str] = Form(...),
    mode: str = Form("now"), scheduled_at: str = Form(""), tz: str = Form(settings.default_timezone),
    session: AsyncSession = Depends(get_session),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(422, "Video must be .mp4 or .mov")
    if mode not in ("now", "schedule"):
        raise HTTPException(422, "mode must be now or schedule")
    try:
        copy_d = json.loads(texts)
        assert isinstance(copy_d, dict)
    except (ValueError, AssertionError):
        raise HTTPException(422, "texts must be a JSON object")
    when = None
    if mode == "schedule":
        when = parse_schedule(scheduled_at, tz)
        if when <= datetime.now(when.tzinfo):
            raise HTTPException(422, "Scheduled time must be in the future")
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size == 0 or size > settings.max_video_mb * 1024 * 1024:
        raise HTTPException(422, f"Video must be between 1 byte and {settings.max_video_mb} MB")

    try:
        accounts = {a["id"]: a for a in await zernio.list_accounts()}
        targets = [accounts[i] for i in account_ids if i in accounts]
        if not targets or len(targets) != len(set(account_ids)):
            raise HTTPException(422, "Choose at least one connected account")
        problem = check_copy(targets, copy_d)
        if problem:
            raise HTTPException(422, problem)
        url = await zernio.upload_video(file.filename, ALLOWED[ext], size, read_chunks(file))
        res = await zernio.create_post(
            url, copy_d, targets, publish_now=mode == "now",
            scheduled_local=scheduled_at if when else None, tz=tz)
    except zernio.ZernioError as e:
        raise HTTPException(e.status if e.status < 500 else 502, e.message)

    post = res.get("post", {})
    group = uuid.uuid4().hex[:12]
    rows = []
    for t in targets:
        row = Publication(
            group_id=group, filename=file.filename, title=copy_d.get(t["platform"], {}).get("title", "")[:120],
            caption=copy_d.get(t["platform"], {}).get("caption", ""), platform=t["platform"],
            account_id=t["id"], account_name=t["username"], mode=mode,
            scheduled_for=when.astimezone(timezone.utc) if when else None,  # SQLite drops tz: store UTC
            timezone=tz, status="SCHEDULED" if when else "PUBLISHING", zernio_post_id=post.get("_id"))
        apply_post(row, post)
        session.add(row)
        rows.append(row)
    await session.commit()
    return {"items": [r.as_dict() for r in rows], "warnings": res.get("warnings", [])}


async def refresh(row: Publication, session: AsyncSession):
    try:
        apply_post(row, await zernio.get_post(row.zernio_post_id))
    except zernio.ZernioError:
        pass  # keep the last known status; the next refresh retries


@router.get("/posts")
async def history(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Publication).order_by(Publication.id.desc()).limit(100))).all()
    open_rows = [r for r in rows if r.status not in FINAL and r.zernio_post_id]
    await asyncio.gather(*(refresh(r, session) for r in open_rows))
    await session.commit()
    return {"items": [r.as_dict() for r in rows]}
