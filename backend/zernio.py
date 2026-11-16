"""Zernio API client - the only file that knows the vendor's wire format.
Swap this module for another provider without touching routes (PH-12)."""
from typing import AsyncIterator
import httpx

from config import settings


class ZernioError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message, self.status = message, status


def _client(timeout: float = 30) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.zernio_base_url, timeout=timeout,
        headers={"Authorization": f"Bearer {settings.zernio_api_key}"})


def _raise(r: httpx.Response):
    if r.status_code >= 400:
        try:
            body = r.json()
            msg = body.get("error") or body.get("message") or str(body)
        except Exception:
            msg = r.text[:300]
        raise ZernioError(f"Zernio {r.status_code}: {msg}", r.status_code)


def _account(a: dict) -> dict:
    pdata = (a.get("metadata") or {}).get("profileData") or {}
    prof = a.get("profileId")
    return {"id": a["_id"], "platform": a["platform"],
            "username": a.get("username") or a.get("displayName") or "",
            "active": a.get("isActive", True) and not a.get("needsReconnection", False),
            "profile_id": prof.get("_id") if isinstance(prof, dict) else prof,
            "avatar": a.get("profilePicture") or pdata.get("profilePicture"),
            "url": a.get("profileUrl"), "followers": pdata.get("followersCount"),
            "connected_at": (a.get("metadata") or {}).get("connectedAt")}


async def list_accounts() -> list[dict]:
    async with _client() as c:
        r = await c.get("/accounts")
        _raise(r)
        return [_account(a) for a in r.json().get("accounts", [])]


async def _default_profile(c: httpx.AsyncClient) -> str:
    r = await c.get("/profiles")
    _raise(r)
    profiles = r.json().get("profiles", [])
    if not profiles:
        raise ZernioError("No Zernio profile found.", 502)
    return next((p for p in profiles if p.get("isDefault")), profiles[0])["_id"]


async def connect_url(platform: str, return_to: str) -> str:
    """OAuth link: the user approves on the platform, then lands back on return_to."""
    async with _client() as c:
        pid = await _default_profile(c)
        r = await c.get(f"/connect/{platform}", params={"profileId": pid, "redirect_url": return_to})
        _raise(r)
        url = r.json().get("authUrl")
        if not url:
            raise ZernioError("Zernio did not return a connect link.", 502)
        return url


async def disconnect_account(account_id: str) -> None:
    async with _client() as c:
        _raise(await c.delete(f"/accounts/{account_id}"))


async def upload_video(filename: str, content_type: str, size: int, chunks: AsyncIterator[bytes]) -> str:
    """Presign, PUT the bytes, return the public URL Zernio will publish from."""
    async with _client() as c:
        r = await c.post("/media/presign", json={"filename": filename, "contentType": content_type})
        _raise(r)
        d = r.json()
    async with httpx.AsyncClient(timeout=600) as up:
        put = await up.put(d["uploadUrl"], content=chunks,
                           headers={"Content-Type": content_type, "Content-Length": str(size)})
        if put.status_code >= 300:
            raise ZernioError(f"Media upload failed ({put.status_code})", 502)
    return d["publicUrl"]


def _target(t: dict, copy: dict) -> dict:
    """One platform entry with its own text. copy[platform] = {caption, title?, tags?}."""
    c = copy.get(t["platform"], {})
    out = {"platform": t["platform"], "accountId": t["id"], "customContent": c.get("caption", "")}
    if t["platform"] == "youtube":  # explicit title, visibility and kids flag (YouTube may block views otherwise)
        out["platformSpecificData"] = {"title": (c.get("title") or "Untitled video")[:100],
                                       "visibility": c.get("visibility", "public"), "madeForKids": False}
    return out


async def create_post(media_url: str, copy: dict, targets: list[dict], *,
                      publish_now: bool, scheduled_local: str | None, tz: str) -> dict:
    first = next((copy.get(t["platform"], {}).get("caption", "") for t in targets), "")
    body: dict = {
        "content": first,
        "mediaItems": [{"type": "video", "url": media_url}],
        "platforms": [_target(t, copy) for t in targets],
    }
    tags = copy.get("youtube", {}).get("tags")
    if tags and any(t["platform"] == "youtube" for t in targets):
        body["tags"] = tags
    if publish_now:
        body["publishNow"] = True
    else:
        body["scheduledFor"], body["timezone"] = scheduled_local, tz
    async with _client(timeout=300) as c:  # publishNow waits for Instagram to process the reel
        r = await c.post("/posts", json=body)
        if r.status_code != 207:
            _raise(r)
        return r.json()


async def get_post(post_id: str) -> dict:
    async with _client() as c:
        r = await c.get(f"/posts/{post_id}")
        _raise(r)
        return r.json().get("post", {})
