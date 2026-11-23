"""Meta Graph API client - the only file that knows Meta's wire format.
Facebook Pages only for now. Instagram and WhatsApp checks are read-only (capabilities)."""
import asyncio
from pathlib import Path

import httpx
from dotenv import dotenv_values

from config import HERE, settings

ENV = HERE / ".env"

HOST = "https://graph.facebook.com"
VIDEO_HOST = "https://graph-video.facebook.com"
EXPIRED = ("The Meta token has expired or is invalid. Generate a new one in the Graph API Explorer "
           "and put it in backend/.env as META_ACCESS_TOKEN, then restart the backend.")


NO_POST = ("The Meta token is missing the pages_manage_posts permission, so Facebook refuses to post on the Page. "
           "In the Graph API Explorer pick your app, add pages_manage_posts (keep pages_show_list and pages_read_engagement), "
           "press Generate Access Token, allow the Page, and paste the new token into backend/.env as META_ACCESS_TOKEN.")
CHUNK = 4 * 1024 * 1024  # Facebook's resumable upload; one-piece uploads of big files are refused with 413


class MetaError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message, self.status = message, status


def _mtime() -> float:
    try:
        return ENV.stat().st_mtime
    except OSError:
        return 0.0


_seen = {"mtime": _mtime()}  # settings were read from .env at start; reload only when the file changes after that


def _fresh_env() -> None:
    """Pick up a new token pasted into backend/.env without restarting the backend."""
    now = _mtime()
    if not now or now == _seen["mtime"]:
        return
    _seen["mtime"] = now
    values = dotenv_values(ENV)
    settings.meta_access_token = values.get("META_ACCESS_TOKEN") or settings.meta_access_token
    settings.threads_access_token = values.get("THREADS_ACCESS_TOKEN") or settings.threads_access_token


def _token() -> str:
    _fresh_env()
    if not settings.meta_access_token:
        raise MetaError("No Meta token. Put it in backend/.env as META_ACCESS_TOKEN.", 400)
    return settings.meta_access_token


def _raise(r: httpx.Response):
    if r.status_code < 400:
        return
    try:
        err = r.json().get("error", {})
    except Exception:
        err = {}
    if err.get("code") == 190:  # OAuthException: token expired, revoked or invalid
        raise MetaError(EXPIRED, 401)
    if err.get("code") in (10, 100, 200) and "permission" in (err.get("message") or "").lower():
        raise MetaError(f"{NO_POST} (Meta said: {err.get('message')})", 403)
    raise MetaError(f"Meta {r.status_code}: {err.get('message') or r.text[:300]}", r.status_code if r.status_code < 500 else 502)


async def _get(path: str, token: str | None = None, **params) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{HOST}/{settings.meta_graph_version}/{path}", params={**params, "access_token": token or _token()})
    _raise(r)
    return r.json()


async def threads_status() -> dict | None:
    """Threads uses its own token and host. None when no Threads token is set."""
    _fresh_env()
    if not settings.threads_access_token:
        return None
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://graph.threads.net/v1.0/me", params={"fields": "id,username", "access_token": settings.threads_access_token})
    if r.status_code >= 400:
        return {"ok": False, "error": (r.json().get("error", {}) or {}).get("message", "Threads rejected the token.")}
    return {"ok": True, **r.json()}


def _capabilities(granted: set[str], pages: list[dict], threads: dict | None = None) -> list[dict]:
    can_post = [p for p in pages if "CREATE_CONTENT" in p["tasks"]]
    ig = [p for p in pages if p.get("instagram")]

    def row(key, label, ok, why):
        return {"key": key, "label": label, "ok": ok, "why": why}
    return [
        row("facebook_video", "Publish video to a Facebook Page",
            "pages_manage_posts" in granted and bool(can_post),
            "Ready." if "pages_manage_posts" in granted and can_post
            else "Needs the pages_manage_posts permission (publish_video alone is not enough for a Page) and a Page where you can create content."),
        row("instagram_video", "Publish video to Instagram",
            "instagram_content_publish" in granted and bool(ig),
            "Ready." if "instagram_content_publish" in granted and ig
            else "Needs instagram_basic and instagram_content_publish, and an Instagram professional account linked to the Page. None is visible to this token."),
        row("threads_video", "Publish video to Threads", bool(threads and threads.get("ok")),
            f"Threads token works for @{threads['username']}." if threads and threads.get("ok")
            else (f"Threads rejected the token: {threads['error']}" if threads
                  else "Needs a Threads token (not a Facebook token) with threads_basic and threads_content_publish. Set THREADS_ACCESS_TOKEN.")),
        row("whatsapp_message", "Send WhatsApp messages",
            {"whatsapp_business_messaging", "whatsapp_business_management"} <= granted,
            "Permissions granted. Sending also needs a WhatsApp Business number, which this check cannot see." if {"whatsapp_business_messaging", "whatsapp_business_management"} <= granted
            else "Needs whatsapp_business_messaging and whatsapp_business_management, and a WhatsApp Business number."),
    ]


async def check() -> dict:
    """Who the token belongs to, what it may do, and which Pages it can reach. Read-only."""
    me = await _get("me", fields="id,name")
    perms = (await _get("me/permissions")).get("data", [])
    granted = {p["permission"] for p in perms if p.get("status") == "granted"}
    raw = (await _get("me/accounts", fields="id,name,category,tasks,instagram_business_account{id,username}", limit=100)).get("data", [])
    pages = [{"id": p["id"], "name": p["name"], "category": p.get("category", ""), "tasks": p.get("tasks", []),
              "instagram": p.get("instagram_business_account")} for p in raw]  # page tokens never leave the server
    threads = await threads_status()
    return {"user": me, "permissions": sorted(granted), "pages": pages, "threads": threads,
            "capabilities": _capabilities(granted, pages, threads)}


async def page_access(page_id: str) -> dict:
    """Name and Page access token (needed to post as the Page). Read from the user's Page list,
    which works with pages_show_list alone."""
    pages = (await _get("me/accounts", fields="id,name,access_token", limit=100)).get("data", [])
    page = next((p for p in pages if p["id"] == page_id), None)
    if not page or not page.get("access_token"):
        raise MetaError("This token cannot post as that Page (no Page access).", 403)
    return page


async def publish_video(page_id: str, token: str, path: str, filename: str, ctype: str, title: str,
                        description: str, scheduled_ts: int | None) -> str:
    """Resumable upload: start (Meta answers with the byte range it wants next), send each range, then finish with the post text."""
    url = f"{VIDEO_HOST}/{settings.meta_graph_version}/{page_id}/videos"
    size = Path(path).stat().st_size
    async with httpx.AsyncClient(timeout=900) as c:
        r = await c.post(url, data={"upload_phase": "start", "file_size": str(size), "access_token": token})
        _raise(r)
        d = r.json()
        vid, session = d.get("video_id"), d.get("upload_session_id")
        if not vid or not session:
            raise MetaError("Meta did not start the video upload.", 502)
        start, end = int(d["start_offset"]), int(d["end_offset"])
        with open(path, "rb") as f:
            while start < end:
                f.seek(start)
                part = f.read(end - start)
                r = await c.post(url, data={"upload_phase": "transfer", "upload_session_id": session, "start_offset": str(start), "access_token": token},
                                 files={"video_file_chunk": (filename, part, ctype)})
                _raise(r)
                start, end = int(r.json()["start_offset"]), int(r.json()["end_offset"])
        data = {"upload_phase": "finish", "upload_session_id": session, "title": title, "description": description, "access_token": token}
        if scheduled_ts:
            data.update({"published": "false", "scheduled_publish_time": str(scheduled_ts), "unpublished_content_type": "SCHEDULED"})
        r = await c.post(url, data=data)
        _raise(r)
    if r.json().get("success") is False:
        raise MetaError("Meta did not accept the finished video.", 502)
    return str(vid)


async def publish_photo(page_id: str, token: str, path: str, filename: str, ctype: str, caption: str,
                        scheduled_ts: int | None) -> dict:
    """Post one image to a Page. Returns {"id": photo id, "post_id": feed post id or None}."""
    data = {"caption": caption, "access_token": token}
    if scheduled_ts:
        data.update({"published": "false", "scheduled_publish_time": str(scheduled_ts), "unpublished_content_type": "SCHEDULED"})
    with open(path, "rb") as f:
        async with httpx.AsyncClient(timeout=300) as c:
            r = await c.post(f"{HOST}/{settings.meta_graph_version}/{page_id}/photos",
                             data=data, files={"source": (filename, f, ctype)})
    _raise(r)
    d = r.json()
    if not d.get("id"):
        raise MetaError("Meta did not return a photo id.", 502)
    return {"id": str(d["id"]), "post_id": d.get("post_id")}


def photo_url(ids: dict) -> str:
    return f"https://www.facebook.com/{ids['post_id']}" if ids.get("post_id") else f"https://www.facebook.com/photo?fbid={ids['id']}"


async def photo_link(page_token: str, photo_id: str) -> str | None:
    """Link of a photo once it exists (a scheduled photo is not readable until it goes live). None if not readable."""
    try:
        return (await _get(photo_id, token=page_token, fields="link")).get("link")
    except MetaError:
        return None


def map_video(v: dict) -> tuple[str, str | None, str | None]:
    """(status, url, error) from a video object."""
    st = (v.get("status") or {}).get("video_status")
    url = v.get("permalink_url")
    url = f"https://www.facebook.com{url}" if url and url.startswith("/") else url
    if st == "error":
        return "FAILED", url, "Facebook could not process the video."
    if st == "processing" or st == "upload_complete":
        return "PUBLISHING", url, None
    if v.get("published") is False:
        return "SCHEDULED", url, None
    return "PUBLISHED", url, None


async def video_state(page_token: str, video_id: str) -> dict:
    return await _get(video_id, token=page_token, fields="status,permalink_url,published,scheduled_publish_time")


async def video_source(page_token: str, video_id: str, limit: int = 180, poll: int = 5) -> str | None:
    """Public link of a Page video once Facebook has processed it (Threads fetches the video from it). None if it never appears."""
    waited = 0
    while waited <= limit:
        try:
            src = (await _get(video_id, token=page_token, fields="source")).get("source")
        except MetaError:
            src = None
        if src:
            return src
        await asyncio.sleep(poll)
        waited += poll or 1
    return None
