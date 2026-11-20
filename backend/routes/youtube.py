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

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import yt_accounts
import yt_publish
import yt_thumbnail
import youtube
from config import settings
from db import get_session
from models import FINAL, Publication
from routes.posts import ALLOWED, CHUNK, parse_schedule

async def select_account(account: str = Query("")):
    """Every YouTube route works on one account: ?account=key, or the first one in YOUTUBE_ACCOUNTS."""
    try:
        yt_accounts.use(account)
    except KeyError:
        raise HTTPException(404, f"Unknown YouTube account '{account}'. Known: {', '.join(yt_accounts.load()) or 'none'}.")


router = APIRouter(prefix="/api/youtube", dependencies=[Depends(select_account)])
PLATFORM = "youtube-direct"  # keeps these rows apart from the Zernio YouTube rows
MIN_AHEAD = 10 * 60
BACK_TO = {"studio": "/studio?tab=access", "accounts": "/accounts", "youtube": ""}  # where to land after signing in, by the `back` value
_states: dict[str, dict] = {}  # sign-in states we issued: which account and where to send the user back (guards the callback)


def _fail(e: youtube.YouTubeError):
    raise HTTPException(e.status, e.message)


@router.get("/accounts")
async def accounts():
    """The accounts named in .env, whether each is set up and signed in. No call to Google."""
    items = []
    for a in yt_accounts.load().values():
        yt_accounts.use(a.key)
        items.append({"key": a.key, "label": a.label, "configured": a.configured, "connected": youtube.connected(), "missing": "" if a.configured else a.env_names})
    return {"accounts": items, "default": yt_accounts.default_key()}


@router.get("/status")
async def status():
    acct = yt_accounts.current()
    out = {"account": acct.key, "label": acct.label, "configured": youtube.configured(), "connected": youtube.connected(), "channel": None, "error": "",
           "redirect_uri": settings.youtube_redirect_uri, "setup_problem": "",
           "categories": [{"id": k, "name": v} for k, v in youtube.CATEGORIES.items()]}
    if out["configured"] and not out["connected"]:
        out["setup_problem"] = await youtube.check_setup()
    if out["connected"]:
        try:
            out["channel"] = await youtube.channel()
        except youtube.YouTubeError as e:
            out["error"], out["connected"] = e.message, youtube.connected()
    return out


@router.get("/connect")
async def connect(reports: bool = False, manage: bool = False, back: str = "", check: bool = False):
    if not youtube.configured():
        raise HTTPException(400, f"Put {yt_accounts.current().env_names or 'YOUTUBE_ACCOUNTS and its client values'} in backend/.env, then restart the backend.")
    redirect = settings.youtube_redirect_uri
    if check:  # ask Google first, so the user is not sent to Google's error page; it also finds which address this client accepts
        redirect, problem = await youtube.accepted_redirect()
        if problem:
            raise HTTPException(409, problem)
    state = secrets.token_urlsafe(16)
    _states[state] = {"account": yt_accounts.current().key, "back": back if back in BACK_TO else "", "redirect": redirect}
    extra = ((youtube.ANALYTICS_SCOPE,) if reports else ()) + ((youtube.MANAGE_SCOPE,) if manage else ())
    return {"url": youtube.auth_url(state, extra, redirect), "redirect_uri": redirect}


@router.get("/callback")
async def callback(code: str = "", state: str = "", error: str = ""):
    if error or state not in _states or not code:
        return RedirectResponse(f"{settings.frontend_url}/#/youtube?error={quote(error or 'The sign-in was cancelled or expired. Try again.')}")
    issued = _states.pop(state)
    yt_accounts.use(issued["account"], strict=False)  # the Google answer belongs to the account that asked
    back = f"{settings.frontend_url}/#/youtube" + BACK_TO.get(issued["back"], "")
    sep = "&" if "?" in back else "?"
    try:
        await youtube.exchange_code(code, issued.get("redirect"))  # the same address the sign-in link used
    except youtube.YouTubeError as e:
        return RedirectResponse(f"{back}{sep}error={quote(e.message)}")
    return RedirectResponse(f"{back}{sep}connected=1&account={issued['account']}")


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


def advanced(category_id: str = Form("22"), made_for_kids: bool = Form(False), language: str = Form(""), license: str = Form("youtube"),
             embeddable: bool = Form(True), public_stats: bool = Form(True), synthetic: bool = Form(False), notify: bool = Form(True)) -> dict:
    """The YouTube advanced options, read from the same form."""
    if category_id not in youtube.CATEGORIES:
        raise HTTPException(422, "Unknown YouTube category")
    if license not in ("youtube", "creativeCommon"):
        raise HTTPException(422, "License must be youtube or creativeCommon")
    return {"category_id": category_id, "made_for_kids": made_for_kids, "language": language.strip()[:10], "license": license,
            "embeddable": embeddable, "public_stats": public_stats, "synthetic": synthetic, "notify": notify}


def _check(file: UploadFile, title: str, description: str, privacy: str) -> str:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(422, "Only MP4 or MOV videos are accepted")
    if not title.strip():
        raise HTTPException(422, "YouTube needs a title")
    if len(title) > 100 or len(description) > 5000:
        raise HTTPException(422, "Title is over 100 characters or description over 5,000")
    if privacy not in ("public", "unlisted", "private"):
        raise HTTPException(422, "Visibility must be public, unlisted or private")
    return ext


def _when(mode: str, scheduled_at: str, tz: str):
    if mode != "schedule":
        return None
    when = parse_schedule(scheduled_at, tz)
    if when.timestamp() - time.time() < MIN_AHEAD:
        raise HTTPException(422, "Schedule at least 10 minutes from now.")
    return when


async def _read_thumbnail(thumb: UploadFile | None) -> tuple[tuple[bytes, str] | None, list[str]]:
    """The thumbnail bytes if valid, else a warning. It is applied after YouTube has processed each video."""
    if not thumb or not thumb.filename:
        return None, []
    ext = Path(thumb.filename).suffix.lower()
    data = await thumb.read()
    if ext not in yt_thumbnail.TYPES or len(data) > 2 * 1024 * 1024:
        return None, ["Thumbnail skipped: it must be a JPG or PNG up to 2 MB."]
    return (data, ext), []


async def _job(file: UploadFile, thumbnail: UploadFile | None, title: str, description: str, tags: str, privacy: str, mode: str,
               scheduled_at: str, tz: str, opts: dict) -> tuple[yt_publish.Job, list[str]]:
    ext = _check(file, title, description, privacy)
    when = _when(mode, scheduled_at, tz)
    thumb, warnings = await _read_thumbnail(thumbnail)
    path, size = await _save_upload(file)
    return yt_publish.Job(path, size, ALLOWED[ext], file.filename, title.strip(), description, _tags(tags), privacy, mode, when, tz, opts, thumb), warnings


@router.post("/posts")
async def create(
    file: UploadFile = File(...), thumbnail: UploadFile | None = File(None), title: str = Form(...), description: str = Form(""),
    tags: str = Form(""), privacy: str = Form("public"), mode: str = Form("now"), scheduled_at: str = Form(""),
    tz: str = Form(settings.default_timezone), opts: dict = Depends(advanced),
):
    """Upload to the one account chosen with ?account=."""
    job, warnings = await _job(file, thumbnail, title, description, tags, privacy, mode, scheduled_at, tz, opts)
    try:
        ok, failed = await yt_publish.publish_many([yt_accounts.current().key], job)
    finally:
        Path(job.path).unlink(missing_ok=True)
    if failed:
        raise HTTPException(failed[0]["status"], failed[0]["error"])
    return {"items": [ok[0]["item"]], "warnings": warnings, "thumbnail": ok[0]["thumbnail"]}


@router.post("/posts/multi")
async def create_multi(
    file: UploadFile = File(...), thumbnail: UploadFile | None = File(None), title: str = Form(...), description: str = Form(""),
    tags: str = Form(""), privacy: str = Form("public"), mode: str = Form("now"), scheduled_at: str = Form(""),
    tz: str = Form(settings.default_timezone), accounts: list[str] = Form(...), opts: dict = Depends(advanced),
):
    """Upload the same video to every chosen account at the same time, with the same details and the same schedule."""
    known = yt_accounts.load()
    keys = list(dict.fromkeys(a.strip().lower() for a in accounts if a.strip()))
    if not keys:
        raise HTTPException(422, "Choose at least one account.")
    unknown = [k for k in keys if k not in known]
    if unknown:
        raise HTTPException(422, f"Unknown YouTube account: {', '.join(unknown)}.")
    job, warnings = await _job(file, thumbnail, title, description, tags, privacy, mode, scheduled_at, tz, opts)
    try:
        ok, failed = await yt_publish.publish_many(keys, job)
    finally:
        Path(job.path).unlink(missing_ok=True)
    return {"items": [r["item"] for r in ok], "errors": [{k: v for k, v in f.items() if k != "status"} for f in failed],
            "warnings": warnings, "thumbnail": "pending" if any(r["thumbnail"] == "pending" for r in ok) else "none"}


async def _refresh(row: Publication):
    yt_accounts.use(row.account_id, strict=False)
    try:
        item = await youtube.video_state(row.zernio_post_id)
    except youtube.YouTubeError:
        return  # keep the last known status; the next refresh retries
    if item is None:
        row.status, row.error = "FAILED", "The video is no longer on YouTube."
        return
    keep = row.error if (row.error or "").startswith("Thumbnail") else None  # a thumbnail note outlives status refreshes
    row.status, note = youtube.map_state(item["status"], row.visibility)
    row.error = note or keep


@router.get("/posts")
async def history(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Publication).where(Publication.platform == PLATFORM)
                                  .order_by(Publication.id.desc()).limit(100))).all()
    if rows:
        await asyncio.gather(*(_refresh(r) for r in rows if r.status not in FINAL and r.zernio_post_id))
        await session.commit()
    return {"items": [r.as_dict() for r in rows]}


# ---------- actions on an existing video (the row's ... menu) ----------
class Patch(BaseModel):
    title: str | None = None
    description: str | None = None
    tags: str | None = None
    privacy: str | None = None          # public | unlisted | private
    scheduled_at: str | None = None     # reschedule: local date and time, with tz
    tz: str = settings.default_timezone
    cancel_schedule: bool = False       # keep it private and drop the publish time


async def _row(session: AsyncSession, row_id: int) -> Publication:
    row = await session.get(Publication, row_id)
    if not row or row.platform != PLATFORM:
        raise HTTPException(404, "That upload is not in the list.")
    yt_accounts.use(row.account_id, strict=False)  # act on the account that owns this upload
    return row


@router.get("/posts/{row_id}/details")
async def details(row_id: int, session: AsyncSession = Depends(get_session)):
    row = await _row(session, row_id)
    try:
        v = await youtube.get_video(row.zernio_post_id)
    except youtube.YouTubeError as e:
        _fail(e)
    if not v:
        raise HTTPException(404, "This video is no longer on YouTube.")
    return {"title": v["snippet"].get("title", ""), "description": v["snippet"].get("description", ""),
            "tags": ", ".join(v["snippet"].get("tags", [])), "privacy": v["status"].get("privacyStatus"),
            "publish_at": v["status"].get("publishAt")}


def _merge(v: dict, p: Patch):
    """Current video + requested change -> the full snippet and status to send back, and the new publish time."""
    sn = {k: v["snippet"][k] for k in youtube.KEEP_SNIPPET if k in v["snippet"]}
    sn["tags"] = v["snippet"].get("tags", [])
    st = {k: v["status"][k] for k in youtube.MUTABLE_STATUS if k in v["status"]}
    if p.title is not None:
        if not p.title.strip() or len(p.title) > 100:
            raise HTTPException(422, "The title is required and must be 100 characters or less.")
        sn["title"] = p.title.strip()
    if p.description is not None:
        if len(p.description) > 5000:
            raise HTTPException(422, "The description must be 5,000 characters or less.")
        sn["description"] = p.description
    if p.tags is not None:
        sn["tags"] = _tags(p.tags)
    when = None
    if p.privacy or p.cancel_schedule:
        if p.privacy and p.privacy not in ("public", "unlisted", "private"):
            raise HTTPException(422, "Visibility must be public, unlisted or private")
        st["privacyStatus"] = p.privacy or "private"
        st.pop("publishAt", None)
    if p.scheduled_at:
        when = parse_schedule(p.scheduled_at, p.tz)
        if when.timestamp() - time.time() < MIN_AHEAD:
            raise HTTPException(422, "Schedule at least 10 minutes from now.")
        st["privacyStatus"], st["publishAt"] = "private", when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return sn, st, when


@router.patch("/posts/{row_id}")
async def edit(row_id: int, p: Patch, session: AsyncSession = Depends(get_session)):
    row = await _row(session, row_id)
    try:
        v = await youtube.get_video(row.zernio_post_id)
        if not v:
            raise HTTPException(404, "This video is no longer on YouTube.")
        sn, st, when = _merge(v, p)
        await youtube.update_video(row.zernio_post_id, sn, st)
    except youtube.YouTubeError as e:
        _fail(e)
    row.title, row.caption = sn["title"][:120], sn.get("description", "")
    if when:
        row.status, row.mode, row.visibility, row.timezone = "SCHEDULED", "schedule", "public", p.tz
        row.scheduled_for, row.error = when.astimezone(timezone.utc), None
    elif p.privacy or p.cancel_schedule:
        row.status, row.mode, row.visibility, row.scheduled_for, row.error = "PUBLISHED", "now", st["privacyStatus"], None, None
    await session.commit()
    return {"item": row.as_dict()}


@router.delete("/posts/{row_id}")
async def delete_video(row_id: int, session: AsyncSession = Depends(get_session)):
    """Permanently deletes the video on YouTube, then removes the row."""
    row = await _row(session, row_id)
    try:
        await youtube.delete_video(row.zernio_post_id)
    except youtube.YouTubeError as e:
        if e.status != 404:  # already gone on YouTube: just clean the list
            _fail(e)
    await session.delete(row)
    await session.commit()
    return {"ok": True}


@router.delete("/posts/{row_id}/local")
async def remove_from_list(row_id: int, session: AsyncSession = Depends(get_session)):
    """Hides the row here only. The video on YouTube is untouched."""
    await session.delete(await _row(session, row_id))
    await session.commit()
    return {"ok": True}
