"""LinkedIn client - the only file that knows LinkedIn's wire format.
OAuth 2.0 sign-in (OpenID Connect + w_member_social), then the Videos API upload and the Posts API."""
import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

import li_accounts
from config import settings

AUTH = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN = "https://www.linkedin.com/oauth/v2/accessToken"
INTROSPECT = "https://www.linkedin.com/oauth/v2/introspectToken"
TOKEN_GENERATOR = "https://www.linkedin.com/developers/tools/oauth/token-generator"
API = "https://api.linkedin.com"
SCOPES = "openid profile email w_member_social"
POST_SCOPE = "w_member_social"
TEXT_MAX = 3000
TITLE_MAX = 100
PORTAL = "https://www.linkedin.com/developers/apps"
APP_PRODUCTS = "In the LinkedIn Developer portal open your app, Products tab, and add both Share on LinkedIn and Sign In with LinkedIn using OpenID Connect."


class LinkedInError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message, self.status = message, status


def configured() -> bool:
    return li_accounts.current().configured


def _file() -> Path:
    return li_accounts.token_path(li_accounts.current().key)


def saved() -> dict:
    try:
        return json.loads(_file().read_text())
    except (OSError, ValueError):
        return {}


def connected() -> bool:
    """Signed in with a sign-in that has not run out. LinkedIn sign-ins last 60 days and cannot be renewed in the background."""
    t = saved()
    return configured() and bool(t.get("access_token")) and t.get("expires_at", 0) > time.time()


def expired() -> bool:
    t = saved()
    return bool(t.get("access_token")) and t.get("expires_at", 0) <= time.time()


# The last sign-in LinkedIn refused for missing permissions, by account key (kept until the next good sign-in).
scope_refused: set[str] = set()
NO_PERMISSIONS = ("No permissions in your LinkedIn app: LinkedIn refused openid, profile, email or w_member_social. "
                  "On its Products tab add Share on LinkedIn and Sign In with LinkedIn using OpenID Connect, then connect again.")


def disconnect() -> None:
    _file().unlink(missing_ok=True)


def redirect_candidates() -> list[str]:
    """The backend address first. The web page's own address is the fallback for an app that lists only that one:
    the page hands the answer to the backend (see main.jsx)."""
    return list(dict.fromkeys([settings.linkedin_redirect_uri, settings.frontend_url]))


def auth_url(state: str, redirect_uri: str | None = None) -> str:
    q = {"response_type": "code", "client_id": li_accounts.current().client_id, "redirect_uri": redirect_uri or settings.linkedin_redirect_uri,
         "state": state, "scope": SCOPES}
    return f"{AUTH}?{urlencode(q)}"


def _fail(r: httpx.Response, what: str):
    if r.status_code < 400:
        return
    try:
        body = r.json()
        msg = body.get("message") or body.get("error_description") or body.get("error") or r.text[:200]
    except ValueError:
        msg = r.text[:200]
    if r.status_code == 401:
        raise LinkedInError("Your LinkedIn sign-in has run out or was withdrawn. Press Connect and sign in again.", 401)
    if r.status_code == 403:
        raise LinkedInError(f"LinkedIn did not allow this ({msg}). {APP_PRODUCTS} Then sign in again.", 403)
    if r.status_code == 429:
        raise LinkedInError("LinkedIn's daily limit was reached (150 requests per member per day). Try again tomorrow.", 429)
    raise LinkedInError(f"LinkedIn {r.status_code} while {what}: {msg}", r.status_code if r.status_code < 500 else 502)


async def _probe(redirect_uri: str) -> str:
    """What LinkedIn says about one redirect address for the current account: "ok", "mismatch", "bad_client" or "unknown"."""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get(auth_url("setup-check", redirect_uri), headers={"User-Agent": "Mozilla/5.0"})
    except httpx.HTTPError:
        return "unknown"  # offline: do not block, the real sign-in will say what is wrong
    t = r.text.lower()
    if "redirect_uri does not match" in t:
        return "mismatch"
    if "client_id is invalid" in t:
        return "bad_client"
    return "ok"


async def accepted_redirect() -> tuple[str, str]:
    """(address to use, problem). problem is "" when LinkedIn accepts one of our addresses."""
    tried = []
    for uri in redirect_candidates():
        verdict = await _probe(uri)
        if verdict == "bad_client":
            return uri, "LinkedIn does not recognise this client ID. Remove the account and add it again with the Client ID from the Auth tab of your LinkedIn app."
        if verdict in ("ok", "unknown"):
            return uri, ""
        tried.append(uri)
    cid = li_accounts.current().client_id
    return tried[0], (f"No redirect URL in your LinkedIn app (Client ID {cid}). On its Auth tab, under Authorized redirect URLs for your app, "
                      f"add {tried[0]} and press Update. One time per LinkedIn app.")


async def check_setup() -> str:
    """Ask LinkedIn whether it will accept our sign-in link. "" when fine. Reads only the sign-in page; nothing is submitted."""
    return (await accepted_redirect())[1]


def _headers(token: str, **more: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Linkedin-Version": settings.linkedin_version, "X-Restli-Protocol-Version": "2.0.0", **more}


async def _userinfo(token: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{API}/v2/userinfo", headers={"Authorization": f"Bearer {token}"})
    _fail(r, "reading your profile")
    return r.json()


async def exchange_code(code: str, redirect_uri: str | None = None) -> None:
    a = li_accounts.current()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(TOKEN, data={"grant_type": "authorization_code", "code": code, "client_id": a.client_id, "client_secret": a.client_secret,
                                      "redirect_uri": redirect_uri or settings.linkedin_redirect_uri})
    if r.status_code >= 400:
        try:
            msg = r.json().get("error_description") or r.text[:200]
        except ValueError:
            msg = r.text[:200]
        raise LinkedInError(f"LinkedIn would not finish the sign-in: {msg}", 400)
    d = r.json()
    await _save_sign_in(d["access_token"], int(time.time()) + int(d.get("expires_in", 5184000)), d.get("scope", ""), "sign-in")
    scope_refused.discard(a.key)


async def _save_sign_in(token: str, expires_at: int, scope: str, via: str) -> None:
    me = await _userinfo(token)
    _file().parent.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps({"access_token": token, "expires_at": expires_at, "scope": scope, "sub": me.get("sub", ""), "name": me.get("name", ""),
                                   "email": me.get("email", ""), "picture": me.get("picture", ""), "via": via}))
    _file().chmod(0o600)


async def connect_with_token(token: str) -> None:
    """Sign in with a token made in the LinkedIn Developer portal's token generator: no redirect URL is involved.
    LinkedIn is asked (with this app's own client ID and secret) whether the token is live, belongs to this app and carries the permissions posting needs."""
    a, token = li_accounts.current(), "".join(token.split())
    if len(token) < 30:
        raise LinkedInError("That does not look like an access token. Copy the whole token from the token generator.", 422)
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(INTROSPECT, data={"client_id": a.client_id, "client_secret": a.client_secret, "token": token})
    if r.status_code == 401:
        raise LinkedInError("LinkedIn did not accept this app's client secret. Remove the account and add it again with the Primary Client Secret.", 400)
    d = r.json() if r.status_code < 400 else {}
    if not d.get("active"):
        raise LinkedInError(f"LinkedIn says this token is not active for this app. In the token generator select the app with Client ID {a.client_id}, generate a new token and copy all of it.", 422)
    granted = (d.get("scope") or "").replace(" ", ",").split(",")
    missing = [s for s in ("openid", "profile", POST_SCOPE) if s not in granted]
    if missing:
        raise LinkedInError(f"This token lacks the permissions {', '.join(missing)}. Generate it again with openid, profile, email and w_member_social ticked. If they are not listed, {APP_PRODUCTS}", 422)
    await _save_sign_in(token, int(d.get("expires_at") or time.time() + 5184000), " ".join(g for g in granted if g), "token")


def _token() -> str:
    if not connected():
        raise LinkedInError("This account is not signed in to LinkedIn." if not expired() else "The LinkedIn sign-in for this account has run out (they last 60 days). Press Connect and sign in again.", 401)
    return saved()["access_token"]


def person() -> str:
    return f"urn:li:person:{saved().get('sub', '')}"


async def profile() -> dict:
    """Who is signed in, asked from LinkedIn (so a withdrawn sign-in shows up)."""
    me = await _userinfo(_token())
    return {"name": me.get("name", ""), "email": me.get("email", ""), "picture": me.get("picture", ""), "granted": saved().get("scope", "").replace(",", " ").split()}


# ---------- posting ----------
_RESERVED = re.compile(r"([|{}@\[\]()<>#\\*_~])")


def escape_text(text: str) -> str:
    """LinkedIn reads these characters as formatting and cuts the post short at them. Escape them, but leave #hashtags alone so they stay hashtags."""
    return "".join(p if re.fullmatch(r"#\w+", p) else _RESERVED.sub(r"\\\1", p) for p in re.split(r"(#\w+)", text))


def post_url(urn: str) -> str:
    return f"https://www.linkedin.com/feed/update/{urn}/"


async def _put_parts(path: str, instructions: list[dict]) -> list[str]:
    ids = []
    async with httpx.AsyncClient(timeout=300) as c:
        with open(path, "rb") as f:
            for part in instructions:
                f.seek(part["firstByte"])
                chunk = f.read(part["lastByte"] - part["firstByte"] + 1)
                r = await c.put(part["uploadUrl"], content=chunk, headers={"Content-Type": "application/octet-stream"})
                if r.status_code >= 400:
                    raise LinkedInError(f"LinkedIn refused part of the video upload ({r.status_code}).", 502)
                ids.append(r.headers.get("etag", "").strip('"'))
    return ids


async def upload_video(path: str, size: int) -> str:
    """Videos API: initialize, send the parts, finalize, then wait briefly for LinkedIn to process it. Returns the video URN."""
    token, owner = _token(), person()
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{API}/rest/videos?action=initializeUpload", headers=_headers(token, **{"Content-Type": "application/json"}),
                         json={"initializeUploadRequest": {"owner": owner, "fileSizeBytes": size, "uploadCaptions": False, "uploadThumbnail": False}})
        _fail(r, "starting the video upload")
        v = r.json()["value"]
        ids = await _put_parts(path, v["uploadInstructions"])
        r = await c.post(f"{API}/rest/videos?action=finalizeUpload", headers=_headers(token, **{"Content-Type": "application/json"}),
                         json={"finalizeUploadRequest": {"video": v["video"], "uploadToken": v.get("uploadToken", ""), "uploadedPartIds": ids}})
        _fail(r, "finishing the video upload")
        await _wait_available(c, token, v["video"])
    return v["video"]


async def _wait_available(c: httpx.AsyncClient, token: str, urn: str, tries: int = 30) -> None:
    """LinkedIn processes the video after the upload. Wait up to about a minute; a post made a little early is still accepted."""
    for _ in range(tries):
        r = await c.get(f"{API}/rest/videos/{quote(urn, safe='')}", headers=_headers(token))
        if r.status_code < 400:
            status = r.json().get("status", "")
            if status == "AVAILABLE":
                return
            if status == "PROCESSING_FAILED":
                raise LinkedInError(f"LinkedIn could not process this video: {r.json().get('processingFailureReason', 'unsupported file')}. Use an MP4 of 3 seconds to 30 minutes.", 422)
        await asyncio.sleep(2)


async def create_post(video_urn: str, text: str, title: str, visibility: str) -> str:
    body = {"author": person(), "commentary": escape_text(text), "visibility": visibility, "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False,
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "content": {"media": {"id": video_urn, **({"title": title} if title else {})}}}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{API}/rest/posts", headers=_headers(_token(), **{"Content-Type": "application/json"}), json=body)
    _fail(r, "creating the post")
    urn = r.headers.get("x-restli-id", "")
    if not urn:
        raise LinkedInError("LinkedIn accepted the post but did not say which one it is.", 502)
    return urn


async def update_text(urn: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{API}/rest/posts/{quote(urn, safe='')}", headers=_headers(_token(), **{"X-RestLi-Method": "PARTIAL_UPDATE", "Content-Type": "application/json"}),
                         json={"patch": {"$set": {"commentary": escape_text(text)}}})
    _fail(r, "changing the post text")


async def delete_post(urn: str) -> None:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.delete(f"{API}/rest/posts/{quote(urn, safe='')}", headers=_headers(_token(), **{"X-RestLi-Method": "DELETE"}))
    _fail(r, "deleting the post")
