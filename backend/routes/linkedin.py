"""LinkedIn (own LinkedIn app): connect a member, post a video now to one or several accounts, read and manage the history."""
import secrets
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import li_accounts
import li_publish
import linkedin
from config import settings
from db import get_session
from models import Publication

CHUNK = 1024 * 1024
BACK_TO = {"accounts": "/accounts", "linkedin": "", "popup": "/done"}  # where to land after signing in; "popup" is a small page that closes the popup window
SIGN_IN_ERRORS = {
    "unauthorized_scope_error": linkedin.NO_PERMISSIONS,
    "user_cancelled_login": "The LinkedIn sign-in was cancelled.",
    "user_cancelled_authorize": "You did not allow the app on LinkedIn.",
}
_states: dict[str, dict] = {}  # sign-in states we issued (prefix linkedin- lets the web page route a fallback answer here): which account, where to go back


async def select_account(account: str = Query("")):
    """Every LinkedIn route works on one account: ?account=key, or the first one added."""
    try:
        li_accounts.use(account)
    except KeyError:
        raise HTTPException(404, f"Unknown LinkedIn account '{account}'. Known: {', '.join(li_accounts.load()) or 'none'}.")


router = APIRouter(prefix="/api/linkedin", dependencies=[Depends(select_account)])


def _fail(e: linkedin.LinkedInError):
    raise HTTPException(e.status, e.message)


def _days_left() -> int | None:
    t = linkedin.saved()
    return max(0, int((t["expires_at"] - time.time()) // 86400)) if t.get("expires_at") else None


@router.get("/accounts")
async def accounts():
    """The accounts added here, whether each is set up and signed in. No call to LinkedIn."""
    items = []
    for a in li_accounts.load().values():
        li_accounts.use(a.key)
        items.append({"key": a.key, "label": a.label, "configured": a.configured, "connected": linkedin.connected(), "expired": linkedin.expired(),
                      "name": linkedin.saved().get("name", "")})
    return {"accounts": items, "default": li_accounts.default_key(), "redirect_uri": settings.linkedin_redirect_uri}


@router.get("/channels/profiles")
async def profiles():
    """Who each signed-in account is, from the saved sign-in (no call to LinkedIn). Feeds the Post to list."""
    out = []
    for a in li_accounts.load().values():
        li_accounts.use(a.key)
        if linkedin.connected():
            t = linkedin.saved()
            out.append({"key": a.key, "title": t.get("name") or a.label, "handle": t.get("email", ""), "kids_channel": False, "verified": True})
    return {"profiles": out}


@router.get("/status")
async def status():
    acct = li_accounts.current()
    out = {"account": acct.key, "label": acct.label, "configured": linkedin.configured(), "connected": linkedin.connected(), "expired": linkedin.expired(),
           "days_left": _days_left(), "profile": None, "error": "", "redirect_uri": settings.linkedin_redirect_uri, "setup_problem": ""}
    if out["configured"] and not out["connected"]:
        out["setup_problem"] = await linkedin.check_setup()
    if out["connected"]:
        try:
            out["profile"] = await linkedin.profile()
        except linkedin.LinkedInError as e:
            out["error"], out["connected"] = e.message, linkedin.connected()
    return out


@router.get("/connect")
async def connect(back: str = "", check: bool = False):
    if not linkedin.configured():
        raise HTTPException(400, "This account has no LinkedIn app yet. Add its client ID and secret on the Accounts screen.")
    redirect, problem = settings.linkedin_redirect_uri, ""
    if check:  # ask LinkedIn which address it accepts; a problem is reported beside the link, never blocks it (LinkedIn's own page has the last word)
        redirect, problem = await linkedin.accepted_redirect()
    state = "linkedin-" + secrets.token_urlsafe(16)
    _states[state] = {"account": li_accounts.current().key, "back": back if back in BACK_TO else "", "redirect": redirect}
    return {"url": linkedin.auth_url(state, redirect), "redirect_uri": redirect, "problem": problem}


@router.get("/callback")
async def callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    issued = _states.pop(state, None)
    back = f"{settings.frontend_url}/#/linkedin" + BACK_TO.get((issued or {}).get("back", ""), "")
    sep = "&" if "?" in back else "?"
    if error or not issued or not code:
        if error == "unauthorized_scope_error" and issued:
            linkedin.scope_refused.add(issued["account"])  # the checklist shows the permissions to-do until a good sign-in
        reason = SIGN_IN_ERRORS.get(error) or error_description or error or "The sign-in was cancelled or expired. Try again."
        return RedirectResponse(f"{back}{sep}error={quote(reason)}" + (f"&account={issued['account']}" if issued else ""))
    li_accounts.use(issued["account"], strict=False)  # LinkedIn's answer belongs to the account that asked
    try:
        await linkedin.exchange_code(code, issued.get("redirect"))  # the same address the sign-in link used
    except linkedin.LinkedInError as e:
        return RedirectResponse(f"{back}{sep}error={quote(e.message)}")
    return RedirectResponse(f"{back}{sep}connected=1&account={issued['account']}")


@router.post("/token")
async def connect_token(body: TokenIn):
    """Sign in with a token from the LinkedIn Developer portal's token generator (no redirect URL needed)."""
    if not linkedin.configured():
        raise HTTPException(400, "This account has no LinkedIn app yet.")
    try:
        await linkedin.connect_with_token(body.access_token)
    except linkedin.LinkedInError as e:
        _fail(e)
    return {"ok": True, "name": linkedin.saved().get("name", "")}


@router.post("/disconnect")
async def disconnect():
    linkedin.disconnect()
    return {"ok": True}


async def _save_upload(file: UploadFile) -> tuple[str, int]:
    size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > settings.max_video_mb * 1024 * 1024:
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(422, f"Video is over {settings.max_video_mb} MB")
            tmp.write(chunk)
    return tmp.name, size


def _check(file: UploadFile, text: str, title: str, visibility: str) -> None:
    if Path(file.filename or "").suffix.lower() != ".mp4":
        raise HTTPException(422, "LinkedIn accepts MP4 videos. Convert a MOV file to MP4 first.")
    if not text.strip():
        raise HTTPException(422, "Write the post text first.")
    if len(text) > linkedin.TEXT_MAX or len(title) > linkedin.TITLE_MAX:
        raise HTTPException(422, f"The post text is limited to {linkedin.TEXT_MAX} characters and the video title to {linkedin.TITLE_MAX}.")
    if visibility not in ("PUBLIC", "CONNECTIONS"):
        raise HTTPException(422, "Visibility must be PUBLIC or CONNECTIONS.")


@router.post("/posts/multi")
async def create_multi(file: UploadFile = File(...), text: str = Form(...), title: str = Form(""), visibility: str = Form("PUBLIC"), accounts: list[str] = Form(...)):
    """Post the same video, text and visibility to every chosen account at the same time. One failing does not stop the others."""
    known = li_accounts.load()
    keys = list(dict.fromkeys(a.strip().lower() for a in accounts if a.strip()))
    if not keys:
        raise HTTPException(422, "Choose at least one account.")
    unknown = [k for k in keys if k not in known]
    if unknown:
        raise HTTPException(422, f"Unknown LinkedIn account: {', '.join(unknown)}.")
    _check(file, text, title.strip(), visibility)
    path, size = await _save_upload(file)
    try:
        ok, failed = await li_publish.publish_many(keys, li_publish.Job(path, size, file.filename, text.strip(), title.strip(), visibility))
    finally:
        Path(path).unlink(missing_ok=True)
    return {"items": ok, "errors": [{k: v for k, v in f.items() if k != "status"} for f in failed], "warnings": []}


@router.get("/posts")
async def history(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Publication).where(Publication.platform == li_publish.PLATFORM).order_by(Publication.id.desc()).limit(100))).all()
    return {"items": [r.as_dict() for r in rows]}


# ---------- actions on an existing post (the row's ... menu) ----------
class TokenIn(BaseModel):
    access_token: str


class Patch(BaseModel):
    text: str


async def _row(session: AsyncSession, row_id: int) -> Publication:
    row = await session.get(Publication, row_id)
    if not row or row.platform != li_publish.PLATFORM:
        raise HTTPException(404, "That post is not in the list.")
    li_accounts.use(row.account_id, strict=False)  # act on the account that owns this post
    return row


@router.get("/posts/{row_id}/details")
async def details(row_id: int, session: AsyncSession = Depends(get_session)):
    """LinkedIn only lets approved apps read posts back, so the text shown is the one this app sent."""
    row = await _row(session, row_id)
    return {"text": row.caption, "title": row.title}


@router.patch("/posts/{row_id}")
async def edit(row_id: int, p: Patch, session: AsyncSession = Depends(get_session)):
    row = await _row(session, row_id)
    if not p.text.strip() or len(p.text) > linkedin.TEXT_MAX:
        raise HTTPException(422, f"The post text is required and limited to {linkedin.TEXT_MAX} characters.")
    try:
        await linkedin.update_text(row.zernio_post_id, p.text.strip())
    except linkedin.LinkedInError as e:
        _fail(e)
    row.caption = p.text.strip()
    await session.commit()
    return {"item": row.as_dict()}


@router.delete("/posts/{row_id}")
async def delete_post(row_id: int, session: AsyncSession = Depends(get_session)):
    """Permanently deletes the post on LinkedIn, then removes the row."""
    row = await _row(session, row_id)
    try:
        await linkedin.delete_post(row.zernio_post_id)
    except linkedin.LinkedInError as e:
        if e.status != 404:  # already gone on LinkedIn: just clean the list
            _fail(e)
    await session.delete(row)
    await session.commit()
    return {"ok": True}


@router.delete("/posts/{row_id}/local")
async def remove_from_list(row_id: int, session: AsyncSession = Depends(get_session)):
    """Hides the row here only. The post on LinkedIn is untouched."""
    await session.delete(await _row(session, row_id))
    await session.commit()
    return {"ok": True}
