"""X (own X app): connect a user with OAuth 2.0 + PKCE, post a video now to one or several accounts, read and manage the history."""
import secrets
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import x_accounts
import x_publish
import xapi
from config import settings
from db import get_session
from models import Publication

CHUNK = 1024 * 1024
TYPES = {".mp4": "video/mp4", ".mov": "video/quicktime"}
BACK_TO = {"accounts": "/accounts", "x": "", "popup": "/done"}  # "popup" lands on a small page that closes the popup window
REPLY = ("everyone", "following", "mentionedUsers")
SIGN_IN_ERRORS = {"access_denied": "You did not allow the app on X."}
_states: dict[str, dict] = {}  # sign-in states we issued: account, where to go back, and the PKCE verifier


async def select_account(account: str = Query("")):
    """Every X route works on one account: ?account=key, or the first one added."""
    try:
        x_accounts.use(account)
    except KeyError:
        raise HTTPException(404, f"Unknown X account '{account}'. Known: {', '.join(x_accounts.load()) or 'none'}.")


router = APIRouter(prefix="/api/x", dependencies=[Depends(select_account)])


def _fail(e: xapi.XError):
    raise HTTPException(e.status, e.message)


@router.get("/accounts")
async def accounts():
    """The accounts added here, whether each is set up and signed in. No call to X."""
    items = []
    for a in x_accounts.load().values():
        x_accounts.use(a.key)
        t = xapi.saved()
        items.append({"key": a.key, "label": a.label, "configured": a.configured, "connected": xapi.connected(), "expired": False,
                      "name": t.get("name", ""), "username": t.get("username", "")})
    return {"accounts": items, "default": x_accounts.default_key(), "redirect_uri": settings.x_redirect_uri}


@router.get("/channels/profiles")
async def profiles():
    """Who each signed-in account is, from the saved sign-in (no call to X). Feeds the Post to list."""
    out = []
    for a in x_accounts.load().values():
        x_accounts.use(a.key)
        if xapi.connected():
            t = xapi.saved()
            out.append({"key": a.key, "title": t.get("name") or a.label, "handle": f"@{t['username']}" if t.get("username") else "", "kids_channel": False, "verified": True})
    return {"profiles": out}


@router.get("/connect")
async def connect(back: str = ""):
    """The X sign-in link. X's page cannot be checked in advance, so X itself says if the callback URL is not listed."""
    if not xapi.configured():
        raise HTTPException(400, "This account has no X app yet. Add its Client ID and Client Secret on the Accounts screen.")
    verifier, challenge = xapi.pkce()
    state = "xsignin-" + secrets.token_urlsafe(16)
    _states[state] = {"account": x_accounts.current().key, "back": back if back in BACK_TO else "", "verifier": verifier}
    return {"url": xapi.auth_url(state, challenge), "redirect_uri": settings.x_redirect_uri, "problem": ""}


@router.get("/callback")
async def callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    issued = _states.pop(state, None)
    back = f"{settings.frontend_url}/#/x" + BACK_TO.get((issued or {}).get("back", ""), "")
    sep = "&" if "?" in back else "?"
    tail = f"&account={issued['account']}" if issued else ""
    if error or not issued or not code:
        reason = SIGN_IN_ERRORS.get(error) or error_description or error or "The sign-in was cancelled or expired. Try again."
        return RedirectResponse(f"{back}{sep}error={quote(reason)}{tail}")
    x_accounts.use(issued["account"], strict=False)  # X's answer belongs to the account that asked
    try:
        await xapi.exchange_code(code, issued["verifier"])
    except xapi.XError as e:
        return RedirectResponse(f"{back}{sep}error={quote(e.message)}{tail}")
    return RedirectResponse(f"{back}{sep}connected=1{tail}")


@router.post("/disconnect")
async def disconnect():
    xapi.disconnect()
    return {"ok": True}


async def _save_upload(file: UploadFile, suffix: str) -> tuple[str, int]:
    size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > settings.max_video_mb * 1024 * 1024:
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(422, f"Video is over {settings.max_video_mb} MB")
            tmp.write(chunk)
    return tmp.name, size


@router.post("/posts/multi")
async def create_multi(file: UploadFile = File(...), text: str = Form(...), reply: str = Form("everyone"), accounts: list[str] = Form(...)):
    """Post the same video and text to every chosen account at the same time. One failing does not stop the others."""
    known = x_accounts.load()
    keys = list(dict.fromkeys(a.strip().lower() for a in accounts if a.strip()))
    if not keys:
        raise HTTPException(422, "Choose at least one account.")
    unknown = [k for k in keys if k not in known]
    if unknown:
        raise HTTPException(422, f"Unknown X account: {', '.join(unknown)}.")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in TYPES:
        raise HTTPException(422, "X accepts MP4 or MOV videos.")
    if not text.strip() or len(text) > xapi.TEXT_MAX:
        raise HTTPException(422, "Write the post text first (X allows 280 characters on a normal account).")
    if reply not in REPLY:
        raise HTTPException(422, "Who can reply must be everyone, following or mentionedUsers.")
    path, size = await _save_upload(file, ext)
    try:
        ok, failed = await x_publish.publish_many(keys, x_publish.Job(path, size, TYPES[ext], file.filename, text.strip(), reply))
    finally:
        Path(path).unlink(missing_ok=True)
    return {"items": ok, "errors": [{k: v for k, v in f.items() if k != "status"} for f in failed], "warnings": []}


@router.get("/posts")
async def history(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Publication).where(Publication.platform == x_publish.PLATFORM).order_by(Publication.id.desc()).limit(100))).all()
    return {"items": [r.as_dict() for r in rows]}


async def _row(session: AsyncSession, row_id: int) -> Publication:
    row = await session.get(Publication, row_id)
    if not row or row.platform != x_publish.PLATFORM:
        raise HTTPException(404, "That post is not in the list.")
    x_accounts.use(row.account_id, strict=False)  # act on the account that owns this post
    return row


@router.get("/posts/{row_id}/details")
async def details(row_id: int, session: AsyncSession = Depends(get_session)):
    row = await _row(session, row_id)
    return {"text": row.caption, "title": row.title}


@router.delete("/posts/{row_id}")
async def delete_post(row_id: int, session: AsyncSession = Depends(get_session)):
    """Permanently deletes the post on X, then removes the row. (X's API has no editing.)"""
    row = await _row(session, row_id)
    try:
        await xapi.delete_post(row.zernio_post_id)
    except xapi.XError as e:
        if e.status != 404:
            _fail(e)
    await session.delete(row)
    await session.commit()
    return {"ok": True}


@router.delete("/posts/{row_id}/local")
async def remove_from_list(row_id: int, session: AsyncSession = Depends(get_session)):
    """Hides the row here only. The post on X is untouched."""
    await session.delete(await _row(session, row_id))
    await session.commit()
    return {"ok": True}
