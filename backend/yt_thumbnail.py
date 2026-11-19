"""A custom thumbnail for an uploaded video, applied only after YouTube has finished processing it.
YouTube may ignore a thumbnail sent earlier, which matters most for Shorts. The file waits on disk, so a restart resumes it."""
import asyncio
import logging
from pathlib import Path

from sqlalchemy import select

import db
import yt_accounts
import youtube
from models import Publication

log = logging.getLogger("yt_thumbnail")
PENDING = Path(__file__).parent / "uploads" / "pending_thumbs"
TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
POLL_S, MAX_POLLS = 10, 90  # 15 minutes
_tasks: set[asyncio.Task] = set()


def stash(account: str, video_id: str, data: bytes, ext: str) -> None:
    PENDING.mkdir(parents=True, exist_ok=True)
    (PENDING / f"{account}~{video_id}{ext}").write_bytes(data)  # the account is part of the name, so a restart knows whose it is


def start(account: str, video_id: str) -> None:
    task = asyncio.create_task(apply(account, video_id))
    _tasks.add(task)  # keep a reference so the task is not garbage collected mid-run
    task.add_done_callback(_tasks.discard)


def resume() -> None:
    """After a restart, carry on with thumbnails that were still waiting."""
    if PENDING.exists():
        for f in PENDING.iterdir():
            account, _, video_id = f.stem.rpartition("~")  # older files have no account: they belong to the first one
            start(account, video_id)


def ready(item: dict) -> bool:
    status = (item.get("processingDetails") or {}).get("processingStatus")
    return status == "succeeded" if status else (item.get("status") or {}).get("uploadStatus") == "processed"


def _explain(e: youtube.YouTubeError) -> str:
    """Google's own wording for this refusal is easy to misread, so say what it means and what to do."""
    if e.status == 403 and "custom video thumbnails" in e.message:
        return ("YouTube has not unlocked custom thumbnails for this channel. Verify the channel at youtube.com/verify, "
                "wait up to a day, then set it in YouTube Studio (Content, the video, Thumbnail). The video itself is fine.")
    return e.message


async def _note(video_id: str, text: str) -> None:
    async with db.SessionLocal() as s:
        row = (await s.scalars(select(Publication).where(Publication.zernio_post_id == video_id, Publication.platform == "youtube-direct"))).first()
        if row:
            row.error = text
            await s.commit()


async def apply(account: str, video_id: str) -> None:
    yt_accounts.use(account, strict=False)
    found = list(PENDING.glob(f"{account}~{video_id}.*")) or list(PENDING.glob(f"{video_id}.*"))
    if not found:
        return
    f = found[0]
    try:
        for _ in range(MAX_POLLS):
            item = await youtube.video_state(video_id)
            if item is None:
                raise youtube.YouTubeError("The video is no longer on YouTube.", 404)
            if ready(item):
                await youtube.set_thumbnail(video_id, str(f), TYPES.get(f.suffix.lower(), "image/jpeg"))
                return
            await asyncio.sleep(POLL_S)
        await _note(video_id, "Thumbnail not set: YouTube was still processing the video after 15 minutes.")
    except youtube.YouTubeError as e:
        await _note(video_id, f"Thumbnail not set: {_explain(e)}")
    except Exception:
        log.exception("thumbnail failed for %s", video_id)
        await _note(video_id, "Thumbnail not set: an unexpected error occurred.")
    finally:
        f.unlink(missing_ok=True)
