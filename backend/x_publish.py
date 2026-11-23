"""Post one video to one or several X accounts at the same time. Each account uses its own sign-in.
The text and reply setting are the same for every account. X has no scheduled posting in its API, so every post goes out now."""
import asyncio
import logging
import uuid
from dataclasses import dataclass

import db
import x_accounts
import xapi
from models import Publication

log = logging.getLogger("x_publish")
PLATFORM = "x"


@dataclass
class Job:
    path: str
    size: int
    ctype: str
    filename: str
    text: str
    reply: str  # everyone | following | mentionedUsers


async def publish_one(key: str, job: Job, group: str) -> dict:
    x_accounts.use(key, strict=False)  # this task's own copy of the context, so accounts never mix
    acct = x_accounts.current()
    media = await xapi.upload_video(job.path, job.size, job.ctype)
    post_id = await xapi.create_post(job.text, media, job.reply)
    t = xapi.saved()
    async with db.SessionLocal() as s:
        row = Publication(group_id=group, filename=job.filename, title=job.text.split("\n")[0][:120], caption=job.text, platform=PLATFORM,
                          account_id=acct.key, account_name=f"@{t['username']}" if t.get("username") else acct.label, mode="now", timezone="UTC",
                          visibility=job.reply, status="PUBLISHED", zernio_post_id=post_id, post_url=xapi.post_url(post_id, t.get("username", "")))  # column holds the post id
        s.add(row)
        await s.commit()
        return row.as_dict()


async def publish_many(keys: list[str], job: Job) -> tuple[list[dict], list[dict]]:
    """Returns (successes, failures). One account failing never stops the others."""
    group = uuid.uuid4().hex[:12]
    results = await asyncio.gather(*(publish_one(k, job, group) for k in keys), return_exceptions=True)
    labels = x_accounts.load()
    ok, failed = [], []
    for key, r in zip(keys, results):
        label = labels[key].label if key in labels else key
        if isinstance(r, xapi.XError):
            failed.append({"account": key, "label": label, "error": r.message, "status": r.status})
        elif isinstance(r, Exception):
            log.error("post to %s failed: %r", key, r)
            failed.append({"account": key, "label": label, "error": "An unexpected error stopped this post.", "status": 500})
        else:
            ok.append(r)
    return ok, failed
