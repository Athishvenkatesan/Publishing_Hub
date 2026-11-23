"""Post one video to one or several LinkedIn accounts at the same time. Each account uses its own sign-in.
The text, title and visibility are the same for every account. LinkedIn has no scheduled posting in its public API, so every post goes out now."""
import asyncio
import logging
import uuid
from dataclasses import dataclass

import db
import li_accounts
import linkedin
from models import Publication

log = logging.getLogger("li_publish")
PLATFORM = "linkedin"


@dataclass
class Job:
    path: str
    size: int
    filename: str
    text: str
    title: str
    visibility: str  # PUBLIC or CONNECTIONS


async def publish_one(key: str, job: Job, group: str) -> dict:
    li_accounts.use(key, strict=False)  # this task's own copy of the context, so accounts never mix
    acct = li_accounts.current()
    video = await linkedin.upload_video(job.path, job.size)
    urn = await linkedin.create_post(video, job.text, job.title, job.visibility)
    async with db.SessionLocal() as s:
        row = Publication(group_id=group, filename=job.filename, title=(job.title or job.text.split("\n")[0])[:120], caption=job.text, platform=PLATFORM,
                          account_id=acct.key, account_name=linkedin.saved().get("name") or acct.label, mode="now", timezone="UTC",
                          visibility=job.visibility.lower(), status="PUBLISHED", zernio_post_id=urn, post_url=linkedin.post_url(urn))  # column holds the post URN
        s.add(row)
        await s.commit()
        return row.as_dict()


async def publish_many(keys: list[str], job: Job) -> tuple[list[dict], list[dict]]:
    """Returns (successes, failures). One account failing never stops the others."""
    group = uuid.uuid4().hex[:12]  # ties the rows of one submission together
    results = await asyncio.gather(*(publish_one(k, job, group) for k in keys), return_exceptions=True)
    labels = li_accounts.load()
    ok, failed = [], []
    for key, r in zip(keys, results):
        label = labels[key].label if key in labels else key
        if isinstance(r, linkedin.LinkedInError):
            failed.append({"account": key, "label": label, "error": r.message, "status": r.status})
        elif isinstance(r, Exception):
            log.error("post to %s failed: %r", key, r)
            failed.append({"account": key, "label": label, "error": "An unexpected error stopped this post.", "status": 500})
        else:
            ok.append(r)
    return ok, failed
