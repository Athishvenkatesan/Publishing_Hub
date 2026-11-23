"""Threads through its own API (graph.threads.net) with its own token (THREADS_ACCESS_TOKEN).
Threads cannot take a file upload: it fetches the video from a public link. This app uses the link of the same video
after it went up on Instagram or Facebook, then makes a container, waits for it, and publishes."""
import asyncio

import httpx

import meta
from config import settings

HOST = "https://graph.threads.net/v1.0"
TEXT_MAX = 500
POLL = 5  # seconds between processing checks
PLATFORM = "threads"
NO_TOKEN = "No Threads token. Put a Threads token (threads_basic, threads_content_publish) in backend/.env as THREADS_ACCESS_TOKEN."


def _token() -> str:
    meta._fresh_env()
    if not settings.threads_access_token:
        raise meta.MetaError(NO_TOKEN, 400)
    return settings.threads_access_token


def _raise(r: httpx.Response, what: str) -> None:
    if r.status_code < 400:
        return
    try:
        err = r.json().get("error", {})
    except ValueError:
        err = {}
    if err.get("code") == 190:
        raise meta.MetaError("The Threads token has expired or is invalid. Make a new one and put it in backend/.env as THREADS_ACCESS_TOKEN.", 401)
    raise meta.MetaError(f"Threads {r.status_code} while {what}: {err.get('message') or r.text[:200]}", r.status_code if r.status_code < 500 else 502)


async def _wait(c: httpx.AsyncClient, container: str, limit: int = 300) -> None:
    waited = 0
    while True:
        r = await c.get(f"{HOST}/{container}", params={"fields": "status,error_message", "access_token": _token()})
        _raise(r, "checking the video")
        d = r.json()
        if d.get("status") in ("FINISHED", "PUBLISHED"):
            return
        if d.get("status") in ("ERROR", "EXPIRED"):
            raise meta.MetaError(f"Threads could not process this video: {d.get('error_message') or d.get('status')}. Threads takes MP4 or MOV up to 5 minutes.", 422)
        if waited >= limit:
            raise meta.MetaError("Threads is still processing the video after 5 minutes. Try again later.", 504)
        await asyncio.sleep(POLL)
        waited += POLL or 1


async def publish_video(video_url: str, text: str) -> dict:
    """Post one video with text. Returns {"id", "url", "username"}."""
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{HOST}/me/threads", data={"media_type": "VIDEO", "video_url": video_url, "text": text[:TEXT_MAX], "access_token": _token()})
        _raise(r, "starting the post")
        container = r.json().get("id")
        if not container:
            raise meta.MetaError("Threads did not start the post.", 502)
        await _wait(c, container)
        r = await c.post(f"{HOST}/me/threads_publish", data={"creation_id": container, "access_token": _token()})
        _raise(r, "publishing")
        post = r.json()["id"]
        r = await c.get(f"{HOST}/{post}", params={"fields": "permalink,username", "access_token": _token()})
        d = r.json() if r.status_code < 400 else {}
    return {"id": str(post), "url": d.get("permalink"), "username": d.get("username", "")}
