"""Facebook Pages: check the Meta token, publish a video now or later, read the history."""
import asyncio
import json
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import meta
import meta_ig
import meta_threads
from config import settings
from db import get_session
from models import FINAL, Publication
from routes.posts import ALLOWED, CHUNK, parse_schedule

IMAGES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
MAX_IMAGE_MB = 10

router = APIRouter(prefix="/api/facebook")
MIN_AHEAD, MAX_AHEAD = 10 * 60, 75 * 24 * 3600  # Facebook accepts schedules 10 minutes to 75 days ahead


def _fail(e: meta.MetaError):
    raise HTTPException(e.status, e.message)


@router.get("/check")
async def check():
    try:
        return await meta.check()
    except meta.MetaError as e:
        _fail(e)


def _schedule_ts(mode: str, scheduled_at: str, tz: str) -> tuple[int | None, datetime | None]:
    if mode != "schedule":
        return None, None
    when = parse_schedule(scheduled_at, tz)
    ahead = when.timestamp() - time.time()
    if ahead < MIN_AHEAD:
        raise HTTPException(422, "Facebook needs a scheduled time at least 10 minutes from now.")
    if ahead > MAX_AHEAD:
        raise HTTPException(422, "Facebook cannot schedule more than 75 days ahead.")
    return int(when.timestamp()), when


async def _save_upload(file: UploadFile, max_mb: int | None = None) -> tuple[str, int]:
    limit_mb = max_mb or settings.max_video_mb
    size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "v.mp4").suffix) as tmp:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > limit_mb * 1024 * 1024:
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(422, f"File is over {limit_mb} MB")
            tmp.write(chunk)
    return tmp.name, size


async def _post_video(session: AsyncSession, page_id: str, path: str, filename: str, ctype: str, title: str,
                      description: str, mode: str, ts: int | None, when: datetime | None, tz: str, group: str) -> Publication:
    page = await meta.page_access(page_id)
    video_id = await meta.publish_video(page_id, page["access_token"], path, filename, ctype, title.strip(), description, ts)
    row = Publication(group_id=group, filename=filename, title=title[:120], caption=description,
                      platform="facebook", account_id=page_id, account_name=page["name"], mode=mode,
                      scheduled_for=when.astimezone(timezone.utc) if when else None, timezone=tz,
                      status="SCHEDULED" if when else "PUBLISHING", zernio_post_id=video_id)  # column holds the video id
    session.add(row)
    await session.commit()
    return row


def _check_video(file: UploadFile, description: str) -> str:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(422, "Only MP4 or MOV videos are accepted")
    if len(description) > 63000:
        raise HTTPException(422, "Description is too long")
    return ALLOWED[ext]


@router.post("/posts")
async def create(
    file: UploadFile = File(...), page_id: str = Form(...), title: str = Form(""), description: str = Form(""),
    mode: str = Form("now"), scheduled_at: str = Form(""), tz: str = Form(settings.default_timezone),
    session: AsyncSession = Depends(get_session),
):
    ctype = _check_video(file, description)
    ts, when = _schedule_ts(mode, scheduled_at, tz)
    path, _ = await _save_upload(file)
    try:
        row = await _post_video(session, page_id, path, file.filename, ctype, title, description, mode, ts, when, tz, uuid.uuid4().hex[:12])
        return {"items": [row.as_dict()]}
    except meta.MetaError as e:
        _fail(e)
    finally:
        Path(path).unlink(missing_ok=True)


async def _post_reel(session: AsyncSession, ig: dict, path: str, filename: str, caption: str, group: str, tz: str) -> tuple[Publication, str | None]:
    done = await meta_ig.publish_reel(ig["id"], path, caption)
    row = Publication(group_id=group, filename=filename, title="", caption=caption, platform=meta_ig.PLATFORM, account_id=ig["id"],
                      account_name=ig["username"], mode="now", timezone=tz, status="PUBLISHED", zernio_post_id=done["id"], post_url=done["url"])
    session.add(row)
    await session.commit()
    return row, done.get("media_url")


async def _public_link(ig_link: str | None, fb_rows: list[Publication]) -> str:
    """Threads fetches the video itself: use the Instagram copy, or the Facebook copy once Facebook has processed it."""
    if ig_link:
        return ig_link
    for row in fb_rows:
        page = await meta.page_access(row.account_id)
        if src := await meta.video_source(page["access_token"], row.zernio_post_id):
            return src
    raise meta.MetaError("Threads needs a public link to the video, and this app gets it from the Instagram or Facebook post. "
                         "Tick Instagram (or Facebook with Publish now) together with Threads.", 422)


async def _post_threads(session: AsyncSession, link: str, filename: str, text: str, group: str, tz: str) -> Publication:
    done = await meta_threads.publish_video(link, text)
    row = Publication(group_id=group, filename=filename, title="", caption=text[:meta_threads.TEXT_MAX], platform=meta_threads.PLATFORM,
                      account_id="me", account_name=done["username"] or "threads", mode="now", timezone=tz, status="PUBLISHED",
                      zernio_post_id=done["id"], post_url=done["url"])
    session.add(row)
    await session.commit()
    return row


@router.post("/posts/multi")
async def create_multi(
    file: UploadFile = File(...), pages: list[str] = Form([]), instagram: list[str] = Form([]), threads: bool = Form(False), title: str = Form(""), description: str = Form(""),
    caption: str = Form(""), mode: str = Form("now"), scheduled_at: str = Form(""), tz: str = Form(settings.default_timezone),
    session: AsyncSession = Depends(get_session),
):
    """The same video to several Facebook Pages and Instagram accounts. One failing does not stop the others; each failure is reported."""
    ctype = _check_video(file, description)
    if not pages and not instagram and not threads:
        raise HTTPException(422, "Tick at least one Facebook Page, Instagram account or Threads.")
    if (instagram or threads) and mode == "schedule":
        raise HTTPException(422, "Instagram and Threads posts go out right away (no scheduling through the API). Untick them to schedule, or choose Publish now.")
    if threads and not (pages or instagram):
        raise HTTPException(422, "Threads needs Instagram or Facebook ticked too: it fetches the video from that post.")
    if len(caption) > meta_ig.CAPTION_MAX:
        raise HTTPException(422, f"The Instagram caption is over {meta_ig.CAPTION_MAX} characters.")
    ts, when = _schedule_ts(mode, scheduled_at, tz)
    path, _ = await _save_upload(file)
    group, ok, failed, fb_rows, ig_link = uuid.uuid4().hex[:12], [], [], [], None
    try:
        for page_id in dict.fromkeys(pages):  # keeps order, drops repeats
            try:
                fb_rows.append(await _post_video(session, page_id, path, file.filename, ctype, title, description, mode, ts, when, tz, group))
                ok.append(fb_rows[-1].as_dict())
            except meta.MetaError as e:
                failed.append({"key": page_id, "label": page_id, "error": e.message})
        linked = {a["id"]: a for a in await meta_ig.accounts()} if instagram else {}
        for ig_id in dict.fromkeys(instagram):
            try:
                if ig_id not in linked:
                    raise meta.MetaError("This Instagram account is not linked to a Page the token reaches.", 403)
                row, link = await _post_reel(session, linked[ig_id], path, file.filename, caption or description, group, tz)
                ok.append(row.as_dict())
                ig_link = ig_link or link
            except meta.MetaError as e:
                failed.append({"key": f"ig:{ig_id}", "label": f"Instagram @{linked.get(ig_id, {}).get('username', ig_id)}", "error": e.message})
        if threads:
            try:
                ok.append((await _post_threads(session, await _public_link(ig_link, fb_rows), file.filename, caption or description, group, tz)).as_dict())
            except meta.MetaError as e:
                failed.append({"key": "threads", "label": "Threads", "error": e.message})
    except meta.MetaError as e:
        _fail(e)
    finally:
        Path(path).unlink(missing_ok=True)
    return {"items": ok, "errors": failed}


def _is_photo(row: Publication) -> bool:
    return Path(row.filename or "").suffix.lower() in IMAGES  # photos and videos share one table; the file type tells them apart


@router.post("/photos")
async def create_photo(
    file: UploadFile = File(...), page_id: str = Form(...), caption: str = Form(""),
    mode: str = Form("now"), scheduled_at: str = Form(""), tz: str = Form(settings.default_timezone),
    session: AsyncSession = Depends(get_session),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in IMAGES:
        raise HTTPException(422, "Only JPG or PNG images are accepted")
    if len(caption) > 63000:
        raise HTTPException(422, "Caption is too long")
    ts, when = _schedule_ts(mode, scheduled_at, tz)
    path, _ = await _save_upload(file, MAX_IMAGE_MB)
    try:
        page = await meta.page_access(page_id)
        ids = await meta.publish_photo(page_id, page["access_token"], path, file.filename, IMAGES[ext], caption, ts)
        row = Publication(group_id=uuid.uuid4().hex[:12], filename=file.filename, title="", caption=caption,
                          platform="facebook", account_id=page_id, account_name=page["name"], mode=mode,
                          scheduled_for=when.astimezone(timezone.utc) if when else None, timezone=tz,
                          status="SCHEDULED" if when else "PUBLISHED", zernio_post_id=ids["id"],
                          post_url=None if when else meta.photo_url(ids))
        session.add(row)
        await session.commit()
        return {"items": [row.as_dict()]}
    except meta.MetaError as e:
        _fail(e)
    finally:
        Path(path).unlink(missing_ok=True)


async def _refresh(row: Publication):
    try:
        page = await meta.page_access(row.account_id)
        if _is_photo(row):
            due = row.scheduled_for and row.scheduled_for.replace(tzinfo=row.scheduled_for.tzinfo or timezone.utc) <= datetime.now(timezone.utc)
            link = await meta.photo_link(page["access_token"], row.zernio_post_id) if due else None
            if link:
                row.status, row.post_url = "PUBLISHED", link
            return
        row.status, url, err = meta.map_video(await meta.video_state(page["access_token"], row.zernio_post_id))
        row.post_url, row.error = url or row.post_url, err
    except meta.MetaError:
        pass  # keep the last known status; the next refresh retries


@router.get("/posts")
async def history(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Publication).where(Publication.platform.in_(["facebook", meta_ig.PLATFORM, meta_threads.PLATFORM]))
                                  .order_by(Publication.id.desc()).limit(100))).all()
    await asyncio.gather(*(_refresh(r) for r in rows if r.platform == "facebook" and r.status not in FINAL and r.zernio_post_id))
    await session.commit()
    return {"items": [r.as_dict() for r in rows]}
