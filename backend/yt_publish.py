"""Upload one video to one or several YouTube accounts at the same time. Each account uses its own sign-in.
Everything the user typed (title, description, tags, visibility, advanced options, schedule, thumbnail) is the same for every account."""
import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import db
import yt_accounts
import yt_thumbnail
import youtube
from models import Publication

log = logging.getLogger("yt_publish")


@dataclass
class Job:
    path: str
    size: int
    ctype: str
    filename: str
    title: str
    description: str
    tags: list[str]
    privacy: str
    mode: str
    when: datetime | None
    tz: str
    opts: dict
    thumb: tuple[bytes, str] | None = None  # (bytes, extension)

    @property
    def publish_at(self) -> str | None:
        return self.when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if self.when else None


async def publish_one(key: str, job: Job, group: str) -> dict:
    yt_accounts.use(key, strict=False)  # this task's own copy of the context, so accounts never mix
    acct = yt_accounts.current()
    vid = await youtube.upload(job.path, job.size, job.ctype, job.title, job.description, job.tags, job.privacy, job.publish_at, job.opts)
    thumb = "none"
    if job.thumb:
        yt_thumbnail.stash(acct.key, vid, *job.thumb)
        thumb = "pending"
    async with db.SessionLocal() as s:
        row = Publication(group_id=group, filename=job.filename, title=job.title[:120], caption=job.description, platform="youtube-direct",
                          account_id=acct.key, account_name=acct.label, mode=job.mode,
                          scheduled_for=job.when.astimezone(timezone.utc) if job.when else None, timezone=job.tz,
                          visibility="public" if job.when else job.privacy, status="SCHEDULED" if job.when else "PUBLISHING",
                          zernio_post_id=vid, post_url=f"https://www.youtube.com/watch?v={vid}")  # column holds the video id
        s.add(row)
        await s.commit()
        item = row.as_dict()
    if thumb == "pending":
        yt_thumbnail.start(acct.key, vid)  # after the commit, so a quick failure can find the row
    return {"item": item, "thumbnail": thumb}


async def publish_many(keys: list[str], job: Job) -> tuple[list[dict], list[dict]]:
    """Returns (successes, failures). One account failing never stops the others."""
    group = uuid.uuid4().hex[:12]  # ties the rows of one submission together
    results = await asyncio.gather(*(publish_one(k, job, group) for k in keys), return_exceptions=True)
    labels = yt_accounts.load()
    ok, failed = [], []
    for key, r in zip(keys, results):
        label = labels[key].label if key in labels else key
        if isinstance(r, youtube.YouTubeError):
            failed.append({"account": key, "label": label, "error": r.message, "status": r.status})
        elif isinstance(r, Exception):
            log.error("upload to %s failed: %r", key, r)
            failed.append({"account": key, "label": label, "error": "An unexpected error stopped this upload.", "status": 500})
        else:
            ok.append(r)
    return ok, failed
