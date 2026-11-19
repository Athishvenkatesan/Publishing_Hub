"""Google / YouTube client - the only file that knows Google's wire format.
OAuth 2.0 web flow with offline access, then a resumable video upload (YouTube Data API v3)."""
import json
from pathlib import Path
from urllib.parse import urlencode

import httpx

from config import settings

AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
TOKEN_FILE = Path(__file__).parent / "youtube_token.json"  # holds the refresh token: git-ignored, keep private
CHUNK = 1024 * 1024


class YouTubeError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message, self.status = message, status


def configured() -> bool:
    return bool(settings.youtube_client_id and settings.youtube_client_secret)


def connected() -> bool:
    return TOKEN_FILE.exists()


def disconnect() -> None:
    TOKEN_FILE.unlink(missing_ok=True)


def auth_url(state: str) -> str:
    q = {"client_id": settings.youtube_client_id, "redirect_uri": settings.youtube_redirect_uri, "response_type": "code",
         "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state}
    return f"{AUTH}?{urlencode(q)}"


def _raise(r: httpx.Response):
    if r.status_code < 400:
        return
    try:
        err = r.json().get("error", {})
        msg = err.get("message") if isinstance(err, dict) else (r.json().get("error_description") or err)
    except Exception:
        msg = r.text[:300]
    raise YouTubeError(f"Google {r.status_code}: {msg}", r.status_code if r.status_code < 500 else 502)


async def exchange_code(code: str) -> None:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(TOKEN, data={"code": code, "client_id": settings.youtube_client_id, "client_secret": settings.youtube_client_secret,
                                      "redirect_uri": settings.youtube_redirect_uri, "grant_type": "authorization_code"})
    _raise(r)
    refresh = r.json().get("refresh_token")
    if not refresh:
        raise YouTubeError("Google gave no refresh token. Remove this app at myaccount.google.com/permissions and connect again.", 400)
    TOKEN_FILE.write_text(json.dumps({"refresh_token": refresh}))
    TOKEN_FILE.chmod(0o600)


async def _access_token() -> str:
    if not connected():
        raise YouTubeError("YouTube is not connected. Press Connect YouTube first.", 401)
    refresh = json.loads(TOKEN_FILE.read_text())["refresh_token"]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(TOKEN, data={"client_id": settings.youtube_client_id, "client_secret": settings.youtube_client_secret,
                                      "refresh_token": refresh, "grant_type": "refresh_token"})
    if r.status_code == 400 and r.json().get("error") == "invalid_grant":
        disconnect()  # revoked, or expired (Google test-mode apps last 7 days)
        raise YouTubeError("The YouTube sign-in expired or was revoked. Press Connect YouTube again.", 401)
    _raise(r)
    return r.json()["access_token"]


async def channel() -> dict | None:
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API}/channels", params={"part": "snippet,statistics", "mine": "true"}, headers={"Authorization": f"Bearer {tok}"})
    _raise(r)
    items = r.json().get("items", [])
    if not items:
        return None
    it = items[0]
    return {"id": it["id"], "title": it["snippet"]["title"], "handle": it["snippet"].get("customUrl", ""),
            "subscribers": it.get("statistics", {}).get("subscriberCount")}


async def _chunks(path: str):
    with open(path, "rb") as f:
        while b := f.read(CHUNK):
            yield b


async def upload(path: str, size: int, ctype: str, title: str, description: str, tags: list[str],
                 privacy: str, publish_at: str | None) -> str:
    """Resumable upload. publish_at (UTC, RFC 3339) makes YouTube publish it later: the video is private until then."""
    status = {"privacyStatus": "private" if publish_at else privacy, "selfDeclaredMadeForKids": False}
    if publish_at:
        status["publishAt"] = publish_at
    meta = {"snippet": {"title": title[:100], "description": description[:5000], "tags": tags, "categoryId": "22"}, "status": status}
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=None) as c:
        init = await c.post(UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"}, json=meta,
                            headers={"Authorization": f"Bearer {tok}", "X-Upload-Content-Type": ctype, "X-Upload-Content-Length": str(size)})
        _raise(init)
        put = await c.put(init.headers["location"], content=_chunks(path), headers={"Content-Type": ctype, "Content-Length": str(size)})
    _raise(put)
    vid = put.json().get("id")
    if not vid:
        raise YouTubeError("YouTube did not return a video id.", 502)
    return vid


async def video_state(video_id: str) -> dict | None:
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API}/videos", params={"part": "status", "id": video_id}, headers={"Authorization": f"Bearer {tok}"})
    _raise(r)
    items = r.json().get("items", [])
    return items[0]["status"] if items else None


def map_state(st: dict, asked: str) -> tuple[str, str | None]:
    """(status, note) from a video's status object. asked = the visibility we requested."""
    up = st.get("uploadStatus")
    if up in ("failed", "rejected", "deleted"):
        return "FAILED", st.get("failureReason") or st.get("rejectionReason") or f"YouTube says: {up}"
    if up != "processed":
        return "PUBLISHING", None
    if st.get("publishAt") and st.get("privacyStatus") == "private":
        return "SCHEDULED", None
    if asked == "public" and st.get("privacyStatus") == "private":
        return "PUBLISHED", "YouTube kept this video private. A new Google project must pass YouTube's audit before it can publish publicly."
    return "PUBLISHED", None
