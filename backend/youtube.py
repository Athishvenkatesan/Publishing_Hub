"""Google / YouTube client - the only file that knows Google's wire format.
OAuth 2.0 web flow with offline access, then a resumable video upload (YouTube Data API v3)."""
import json
from pathlib import Path
from urllib.parse import urlencode

import httpx

import yt_accounts
from config import settings

AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
CHUNK = 1024 * 1024
THUMB = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
CATEGORIES = {"1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music", "15": "Pets & Animals", "17": "Sports",
              "19": "Travel & Events", "20": "Gaming", "22": "People & Blogs", "23": "Comedy", "24": "Entertainment",
              "25": "News & Politics", "26": "Howto & Style", "27": "Education", "28": "Science & Technology",
              "29": "Nonprofits & Activism"}
DEFAULT_OPTS = {"category_id": "22", "made_for_kids": False, "language": "", "license": "youtube", "embeddable": True,
                "public_stats": True, "synthetic": False, "notify": True}


class YouTubeError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message, self.status = message, status


def configured() -> bool:
    return yt_accounts.current().configured


def _token_file() -> Path:
    return yt_accounts.token_path(yt_accounts.current().key)


def connected() -> bool:
    return configured() and _token_file().exists()


def disconnect() -> None:
    _token_file().unlink(missing_ok=True)


VERIFY_URL = "https://www.youtube.com/verify"
ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
MANAGE_SCOPE = "https://www.googleapis.com/auth/youtube"  # edit and delete videos (youtube.upload is not accepted for those)


def redirect_candidates() -> list[str]:
    """Where Google may send the user back. The backend address is preferred. The web page's own address is the fallback:
    a client that lists only that one (a common slip: the JavaScript origin pasted into the redirect list) still works,
    because the page hands the answer to the backend (see main.jsx)."""
    return list(dict.fromkeys([settings.youtube_redirect_uri, settings.frontend_url]))


def auth_url(state: str, extra_scopes: tuple[str, ...] = (), redirect_uri: str | None = None) -> str:
    q = {"client_id": yt_accounts.current().client_id, "redirect_uri": redirect_uri or settings.youtube_redirect_uri, "response_type": "code",
         "scope": " ".join([SCOPES, *extra_scopes]), "access_type": "offline", "prompt": "consent", "state": state,
         "include_granted_scopes": "true"}
    return f"{AUTH}?{urlencode(q)}"


def _raise(r: httpx.Response):
    if r.status_code < 400:
        return
    try:
        body = r.json()
        err = body.get("error", {})
        msg = err.get("message") if isinstance(err, dict) else (body.get("error_description") or err)
        reason = (err.get("errors") or [{}])[0].get("reason", "") if isinstance(err, dict) else ""
    except Exception:
        msg, reason = r.text[:300], ""
    if r.status_code == 403 and ("insufficientPermissions" in reason or "insufficient authentication scopes" in str(msg).lower()):
        raise YouTubeError("Your YouTube sign-in does not allow this yet. Open Studio management, then Access, and add the missing permission.", 403)
    raise YouTubeError(f"Google {r.status_code}: {msg}", r.status_code if r.status_code < 500 else 502)


async def _probe(redirect_uri: str) -> str:
    """What Google says about one redirect address for the current account: "ok", "mismatch", "bad_client", or "unknown" (could not ask)."""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get(auth_url("setup-check", redirect_uri=redirect_uri), headers={"User-Agent": "Mozilla/5.0"})
    except httpx.HTTPError:
        return "unknown"  # offline or Google unreachable: do not block, the real sign-in will say what is wrong
    t = r.text.lower()
    if "redirect_uri_mismatch" in t:
        return "mismatch"
    if "invalid_client" in t or "deleted_client" in t or "disabled_client" in t:
        return "bad_client"
    return "ok"


async def accepted_redirect() -> tuple[str, str]:
    """(address to use, problem). Tries the backend address, then the web page's own address. problem is "" when one works."""
    tried = []
    for uri in redirect_candidates():
        verdict = await _probe(uri)
        if verdict == "bad_client":
            return "", f"Google does not recognise this client ID. {yt_accounts.current().fix_hint}"
        if verdict in ("ok", "unknown"):
            return uri, ""
        tried.append(uri)
    return "", (f"Google does not accept this app's sign-in for this account yet. Its client lists neither {tried[0]} nor {tried[-1]} as a redirect address. "
                "Fix it one of two ways: (1) in Google Cloud, open APIs & Services, Credentials, this OAuth client, add "
                f"{tried[0]} under Authorized redirect URIs (not under JavaScript origins), press Save and wait a few minutes; or (2) create a Desktop app OAuth client "
                "instead, which needs no redirect address, and use its client ID and secret. Then press Check again.")


async def check_setup() -> str:
    """Ask Google whether it will accept our sign-in link. "" when fine, else a plain-language problem.
    Reads only Google's sign-in page; nothing is submitted."""
    return (await accepted_redirect())[1]


async def exchange_code(code: str, redirect_uri: str | None = None) -> None:
    acct = yt_accounts.current()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(TOKEN, data={"code": code, "client_id": acct.client_id, "client_secret": acct.client_secret,
                                      "redirect_uri": redirect_uri or settings.youtube_redirect_uri, "grant_type": "authorization_code"})  # must equal the address in the sign-in link
    _raise(r)
    refresh = r.json().get("refresh_token")
    if not refresh:
        raise YouTubeError("Google gave no refresh token. Remove this app at myaccount.google.com/permissions and connect again.", 400)
    path = _token_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"refresh_token": refresh}))
    path.chmod(0o600)


async def _access_token() -> str:
    if not connected():
        raise YouTubeError("YouTube is not connected for this account. Press Connect YouTube first.", 401)
    acct = yt_accounts.current()
    refresh = json.loads(_token_file().read_text())["refresh_token"]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(TOKEN, data={"client_id": acct.client_id, "client_secret": acct.client_secret,
                                      "refresh_token": refresh, "grant_type": "refresh_token"})
    if r.status_code == 400 and r.json().get("error") == "invalid_grant":
        disconnect()  # revoked, or expired (Google test-mode apps last 7 days)
        raise YouTubeError("The YouTube sign-in expired or was revoked. Press Connect YouTube again.", 401)
    _raise(r)
    return r.json()["access_token"]


async def channel() -> dict | None:
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API}/channels", params={"part": "snippet,statistics,status", "mine": "true"}, headers={"Authorization": f"Bearer {tok}"})
    _raise(r)
    items = r.json().get("items", [])
    if not items:
        return None
    it = items[0]
    long_uploads = it.get("status", {}).get("longUploadsStatus")
    return {"id": it["id"], "title": it["snippet"]["title"], "handle": it["snippet"].get("customUrl", ""),
            "subscribers": it.get("statistics", {}).get("subscriberCount"),
            "long_uploads": long_uploads,
            # "allowed" means the channel finished YouTube's phone verification. Custom thumbnails and long videos both need it.
            "verified": long_uploads == "allowed" if long_uploads else None, "verify_url": VERIFY_URL}


async def _chunks(path: str):
    with open(path, "rb") as f:
        while b := f.read(CHUNK):
            yield b


def _metadata(title: str, description: str, tags: list[str], privacy: str, publish_at: str | None, o: dict) -> dict:
    snippet = {"title": title[:100], "description": description[:5000], "tags": tags, "categoryId": o["category_id"]}
    if o["language"]:
        snippet["defaultLanguage"] = o["language"]
    status = {"privacyStatus": "private" if publish_at else privacy, "selfDeclaredMadeForKids": o["made_for_kids"],
              "license": o["license"], "embeddable": o["embeddable"], "publicStatsViewable": o["public_stats"],
              "containsSyntheticMedia": o["synthetic"]}
    if publish_at:
        status["publishAt"] = publish_at
    return {"snippet": snippet, "status": status}


async def upload(path: str, size: int, ctype: str, title: str, description: str, tags: list[str],
                 privacy: str, publish_at: str | None, opts: dict | None = None) -> str:
    """Resumable upload. publish_at (UTC, RFC 3339) makes YouTube publish it later: the video is private until then."""
    o = {**DEFAULT_OPTS, **(opts or {})}
    meta = _metadata(title, description, tags, privacy, publish_at, o)
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=None) as c:
        init = await c.post(UPLOAD, params={"uploadType": "resumable", "part": "snippet,status", "notifySubscribers": str(o["notify"]).lower()},
                            json=meta, headers={"Authorization": f"Bearer {tok}", "X-Upload-Content-Type": ctype, "X-Upload-Content-Length": str(size)})
        _raise(init)
        put = await c.put(init.headers["location"], content=_chunks(path), headers={"Content-Type": ctype, "Content-Length": str(size)})
    _raise(put)
    vid = put.json().get("id")
    if not vid:
        raise YouTubeError("YouTube did not return a video id.", 502)
    return vid


MUTABLE_STATUS = ("privacyStatus", "publishAt", "license", "embeddable", "publicStatsViewable", "selfDeclaredMadeForKids", "containsSyntheticMedia")
KEEP_SNIPPET = ("title", "description", "categoryId", "defaultLanguage")


async def get_video(video_id: str) -> dict | None:
    """Current snippet and status. An update must send these back in full, or YouTube erases what is left out."""
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API}/videos", params={"part": "snippet,status", "id": video_id}, headers={"Authorization": f"Bearer {tok}"})
    _raise(r)
    items = r.json().get("items", [])
    return items[0] if items else None


async def update_video(video_id: str, snippet: dict, status: dict) -> None:
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.put(f"{API}/videos", params={"part": "snippet,status"}, json={"id": video_id, "snippet": snippet, "status": status},
                        headers={"Authorization": f"Bearer {tok}"})
    _raise(r)


async def delete_video(video_id: str) -> None:
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.delete(f"{API}/videos", params={"id": video_id}, headers={"Authorization": f"Bearer {tok}"})
    _raise(r)


async def set_thumbnail(video_id: str, path: str, ctype: str) -> None:
    """Custom thumbnail (JPG or PNG, up to 2 MB). The channel must be verified by phone with YouTube."""
    tok = await _access_token()
    data = Path(path).read_bytes()
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(THUMB, params={"videoId": video_id}, content=data, headers={"Authorization": f"Bearer {tok}", "Content-Type": ctype})
    _raise(r)


async def video_state(video_id: str) -> dict | None:
    """The video's status and processing details, or None when it is not on YouTube."""
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API}/videos", params={"part": "status,processingDetails", "id": video_id}, headers={"Authorization": f"Bearer {tok}"})
    _raise(r)
    items = r.json().get("items", [])
    return items[0] if items else None


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
