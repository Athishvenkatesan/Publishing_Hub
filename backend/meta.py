"""Meta Graph API client - the only file that knows Meta's wire format.
Facebook Pages only for now. Instagram and WhatsApp checks are read-only (capabilities)."""
import httpx

from config import settings

HOST = "https://graph.facebook.com"
VIDEO_HOST = "https://graph-video.facebook.com"
EXPIRED = ("The Meta token has expired or is invalid. Generate a new one in the Graph API Explorer "
           "and put it in backend/.env as META_ACCESS_TOKEN, then restart the backend.")


class MetaError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message, self.status = message, status


def _token() -> str:
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
    raise MetaError(f"Meta {r.status_code}: {err.get('message') or r.text[:300]}", r.status_code if r.status_code < 500 else 502)


async def _get(path: str, token: str | None = None, **params) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{HOST}/{settings.meta_graph_version}/{path}", params={**params, "access_token": token or _token()})
    _raise(r)
    return r.json()


def _capabilities(granted: set[str], pages: list[dict]) -> list[dict]:
    can_post = [p for p in pages if "CREATE_CONTENT" in p["tasks"]]
    ig = [p for p in pages if p.get("instagram")]

    def row(key, label, ok, why):
        return {"key": key, "label": label, "ok": ok, "why": why}
    return [
        row("facebook_video", "Publish video to a Facebook Page",
            "pages_manage_posts" in granted and bool(can_post),
            "Ready." if "pages_manage_posts" in granted and can_post
            else "Needs the pages_manage_posts permission and a Page where you can create content."),
        row("instagram_video", "Publish video to Instagram",
            "instagram_content_publish" in granted and bool(ig),
            "Ready." if "instagram_content_publish" in granted and ig
            else "Needs instagram_content_publish and an Instagram professional account linked to a Page."),
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
    return {"user": me, "permissions": sorted(granted), "pages": pages, "capabilities": _capabilities(granted, pages)}


async def page_access(page_id: str) -> dict:
    """Name and Page access token (needed to post as the Page)."""
    d = await _get(page_id, fields="name,access_token")
    if not d.get("access_token"):
        raise MetaError("This token cannot post as that Page (no Page access).", 403)
    return d


async def publish_video(page_id: str, token: str, path: str, filename: str, ctype: str, title: str,
                        description: str, scheduled_ts: int | None) -> str:
    data = {"title": title, "description": description, "access_token": token}
    if scheduled_ts:
        data.update({"published": "false", "scheduled_publish_time": str(scheduled_ts), "unpublished_content_type": "SCHEDULED"})
    with open(path, "rb") as f:
        async with httpx.AsyncClient(timeout=900) as c:
            r = await c.post(f"{VIDEO_HOST}/{settings.meta_graph_version}/{page_id}/videos",
                             data=data, files={"source": (filename, f, ctype)})
    _raise(r)
    vid = r.json().get("id")
    if not vid:
        raise MetaError("Meta did not return a video id.", 502)
    return str(vid)


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
