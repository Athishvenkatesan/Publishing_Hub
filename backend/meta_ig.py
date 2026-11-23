"""Instagram through the Meta Graph API (the Instagram professional account linked to a Facebook Page).
A video becomes a Reel: make a container, upload the file to Meta's resumable endpoint, wait for processing, publish."""
import asyncio
from pathlib import Path

import httpx

import meta
from config import settings

RUPLOAD = "https://rupload.facebook.com/ig-api-upload"
CAPTION_MAX = 2200
POLL = 5  # seconds between processing checks
PLATFORM = "instagram-meta"  # keeps these rows apart from the Zernio Instagram rows


async def accounts() -> list[dict]:
    """Instagram accounts linked to the Pages this token reaches: [{id, username, page}]."""
    pages = (await meta._get("me/accounts", fields="id,name,instagram_business_account{id,username}", limit=100)).get("data", [])
    return [{"id": p["instagram_business_account"]["id"], "username": p["instagram_business_account"].get("username", ""), "page": p["name"]}
            for p in pages if p.get("instagram_business_account")]


def _url(path: str) -> str:
    return f"{meta.HOST}/{settings.meta_graph_version}/{path}"


async def _container(c: httpx.AsyncClient, ig_id: str, caption: str) -> tuple[str, str]:
    r = await c.post(_url(f"{ig_id}/media"), data={"media_type": "REELS", "upload_type": "resumable", "caption": caption,
                                                   "share_to_feed": "true", "access_token": meta._token()})
    meta._raise(r)
    d = r.json()
    if not d.get("id"):
        raise meta.MetaError("Instagram did not create the upload.", 502)
    return d["id"], d.get("uri") or f"{RUPLOAD}/{settings.meta_graph_version}/{d['id']}"


async def _wait(c: httpx.AsyncClient, container: str, limit: int = 300) -> None:
    waited = 0
    while True:
        r = await c.get(_url(container), params={"fields": "status_code,status", "access_token": meta._token()})
        meta._raise(r)
        d = r.json()
        code = d.get("status_code")
        if code in ("FINISHED", "PUBLISHED"):
            return
        if code in ("ERROR", "EXPIRED"):
            raise meta.MetaError(f"Instagram could not process this video ({d.get('status') or code}). Reels need MP4 or MOV, H.264 video, AAC sound, 3 seconds to 15 minutes.", 422)
        if waited >= limit:
            raise meta.MetaError("Instagram is still processing the video after 5 minutes. Try again later.", 504)
        await asyncio.sleep(POLL)
        waited += POLL or 1


async def publish_reel(ig_id: str, path: str, caption: str) -> dict:
    """Post one video as a Reel. Returns {"id": media id, "url": permalink or None}."""
    size = Path(path).stat().st_size
    async with httpx.AsyncClient(timeout=900) as c:
        container, upload_uri = await _container(c, ig_id, caption)
        with open(path, "rb") as f:
            r = await c.post(upload_uri, content=f.read(),
                             headers={"Authorization": f"OAuth {meta._token()}", "offset": "0", "file_size": str(size)})
        if r.status_code >= 400:
            raise meta.MetaError(f"Instagram refused the video upload ({r.status_code}): {r.text[:200]}", 502)
        await _wait(c, container)
        r = await c.post(_url(f"{ig_id}/media_publish"), data={"creation_id": container, "access_token": meta._token()})
        meta._raise(r)
        media = r.json().get("id")
        if not media:
            raise meta.MetaError("Instagram did not return the post id.", 502)
        r = await c.get(_url(media), params={"fields": "permalink,media_url", "access_token": meta._token()})
    d = r.json() if r.status_code < 400 else {}
    return {"id": str(media), "url": d.get("permalink"), "media_url": d.get("media_url")}  # media_url is a public link Threads can fetch
