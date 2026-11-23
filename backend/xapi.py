"""X (Twitter) client - the only file that knows X's wire format.
OAuth 2.0 with PKCE (offline.access gives a refresh token, so the sign-in renews itself), the v2 chunked media upload, and posts."""
import asyncio
import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

import x_accounts
from config import settings

AUTH = "https://x.com/i/oauth2/authorize"
TOKEN = "https://api.x.com/2/oauth2/token"
REVOKE = "https://api.x.com/2/oauth2/revoke"
API = "https://api.x.com/2"
SCOPES = "tweet.read tweet.write users.read media.write offline.access"
NEEDED = ("tweet.write", "media.write", "offline.access")
SEGMENT = 4 * 1024 * 1024  # X allows up to 5 MB per part
TEXT_MAX = 25000  # Premium accounts; normal accounts are limited to 280 by X itself
PORTAL = "https://developer.x.com/en/portal/dashboard"
SETTINGS_HINT = ("In the X Developer Console open your app, User authentication settings: App permissions Read and write, "
                 "Type of App Web App, Automated App or Bot, and the callback URL shown here.")


class XError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message, self.status = message, status


def configured() -> bool:
    return x_accounts.current().configured


def _file() -> Path:
    return x_accounts.token_path(x_accounts.current().key)


def saved() -> dict:
    try:
        return json.loads(_file().read_text())
    except (OSError, ValueError):
        return {}


def connected() -> bool:
    """Signed in: an access token, or a refresh token that renews it without asking the user again."""
    t = saved()
    return configured() and bool(t.get("refresh_token") or (t.get("access_token") and t.get("expires_at", 0) > time.time()))


def disconnect() -> None:
    _file().unlink(missing_ok=True)


def pkce() -> tuple[str, str]:
    """(verifier, challenge) for PKCE S256."""
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def auth_url(state: str, challenge: str) -> str:
    q = {"response_type": "code", "client_id": x_accounts.current().client_id, "redirect_uri": settings.x_redirect_uri, "scope": SCOPES,
         "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
    return f"{AUTH}?{urlencode(q)}"


def _message(r: httpx.Response) -> str:
    try:
        b = r.json()
    except ValueError:
        return r.text[:200]
    errs = b.get("errors") or []
    return b.get("detail") or b.get("error_description") or (errs[0].get("message") if errs else "") or b.get("title") or b.get("error") or r.text[:200]


def _fail(r: httpx.Response, what: str):
    if r.status_code < 400:
        return
    msg = _message(r)
    if r.status_code == 401:
        raise XError("Your X sign-in has run out or was withdrawn. Press Connect and sign in again.", 401)
    if r.status_code == 402 or "credit" in msg.lower():
        raise XError("Your X API credits have run out. Buy credits (or turn on auto-recharge) in the X Developer Console, then try again.", 402)
    if r.status_code == 403:
        raise XError(f"X did not allow this ({msg}). {SETTINGS_HINT}", 403)
    if r.status_code == 429:
        raise XError("X's rate limit was reached. Wait a little and try again.", 429)
    raise XError(f"X {r.status_code} while {what}: {msg}", r.status_code if r.status_code < 500 else 502)


async def _me(token: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{API}/users/me", headers={"Authorization": f"Bearer {token}"})
    _fail(r, "reading your profile")
    return r.json().get("data", {})


def _store(d: dict, me: dict | None = None) -> None:
    old = saved()
    t = {"access_token": d["access_token"], "refresh_token": d.get("refresh_token") or old.get("refresh_token", ""),
         "expires_at": int(time.time()) + int(d.get("expires_in", 7200)), "scope": d.get("scope", old.get("scope", "")),
         "id": (me or old).get("id", ""), "name": (me or old).get("name", ""), "username": (me or old).get("username", "")}
    _file().parent.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps(t))
    _file().chmod(0o600)


async def _token_call(data: dict) -> httpx.Response:
    a = x_accounts.current()
    async with httpx.AsyncClient(timeout=30) as c:  # a confidential client authenticates with Basic client_id:client_secret
        return await c.post(TOKEN, data={**data, "client_id": a.client_id}, auth=(a.client_id, a.client_secret))


async def exchange_code(code: str, verifier: str) -> None:
    r = await _token_call({"grant_type": "authorization_code", "code": code, "redirect_uri": settings.x_redirect_uri, "code_verifier": verifier})
    if r.status_code >= 400:
        raise XError(f"X would not finish the sign-in: {_message(r)}. Check the Client ID and Client Secret, and that the app is a Web App (confidential client).", 400)
    d = r.json()
    _store(d, await _me(d["access_token"]))


async def _token() -> str:
    """A live access token. X access tokens last 2 hours; the refresh token renews them (and is replaced each time)."""
    t = saved()
    if not configured() or not t:
        raise XError("This account is not signed in to X.", 401)
    if t.get("access_token") and t.get("expires_at", 0) - 120 > time.time():
        return t["access_token"]
    if not t.get("refresh_token"):
        raise XError("The X sign-in has run out. Press Connect and sign in again.", 401)
    r = await _token_call({"grant_type": "refresh_token", "refresh_token": t["refresh_token"]})
    if r.status_code >= 400:
        raise XError("X would not renew the sign-in (it was withdrawn or is too old). Press Connect and sign in again.", 401)
    _store(r.json())
    return saved()["access_token"]


async def profile() -> dict:
    me = await _me(await _token())
    return {"name": me.get("name", ""), "username": me.get("username", ""), "granted": saved().get("scope", "").split()}


def post_url(post_id: str, username: str = "") -> str:
    return f"https://x.com/{username or 'i/web'}/status/{post_id}"


async def upload_video(path: str, size: int, ctype: str) -> str:
    """v2 chunked upload: initialize, send 4 MB parts, finalize, then wait for X to process the video. Returns the media id."""
    h = {"Authorization": f"Bearer {await _token()}"}
    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.post(f"{API}/media/upload/initialize", headers=h, json={"media_type": ctype, "total_bytes": size, "media_category": "tweet_video"})
        _fail(r, "starting the video upload")
        mid = r.json()["data"]["id"]
        with open(path, "rb") as f:
            i = 0
            while chunk := f.read(SEGMENT):
                r = await c.post(f"{API}/media/upload/{mid}/append", headers=h, data={"segment_index": str(i)}, files={"media": ("part", chunk, "application/octet-stream")})
                _fail(r, "sending the video")
                i += 1
        r = await c.post(f"{API}/media/upload/{mid}/finalize", headers=h)
        _fail(r, "finishing the video upload")
        info = r.json().get("data", {}).get("processing_info")
        await _wait_processed(c, h, mid, info)
    return mid


async def _wait_processed(c: httpx.AsyncClient, h: dict, mid: str, info: dict | None, limit: int = 300) -> None:
    waited = 0
    while info and info.get("state") not in ("succeeded", None):
        if info.get("state") == "failed":
            raise XError(f"X could not process this video: {(info.get('error') or {}).get('message', 'unsupported file')}. Use an MP4 (H.264 + AAC).", 422)
        if waited > limit:
            raise XError("X is still processing the video after 5 minutes. Try again later.", 504)
        step = min(int(info.get("check_after_secs", 2)), 10)
        await asyncio.sleep(step)
        waited += step
        r = await c.get(f"{API}/media/upload", headers=h, params={"command": "STATUS", "media_id": mid})
        _fail(r, "checking the video")
        info = r.json().get("data", {}).get("processing_info")


async def create_post(text: str, media_id: str, reply: str) -> str:
    body = {"text": text, "media": {"media_ids": [media_id]}}
    if reply in ("following", "mentionedUsers"):
        body["reply_settings"] = reply
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{API}/tweets", headers={"Authorization": f"Bearer {await _token()}"}, json=body)
    _fail(r, "creating the post")
    return r.json()["data"]["id"]


async def delete_post(post_id: str) -> None:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.delete(f"{API}/tweets/{post_id}", headers={"Authorization": f"Bearer {await _token()}"})
    _fail(r, "deleting the post")
