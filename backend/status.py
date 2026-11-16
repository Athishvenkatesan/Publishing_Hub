"""Map Zernio per-platform state to the status shown in the history table."""
from datetime import datetime

MAP = {"published": "PUBLISHED", "failed": "FAILED", "cancelled": "CANCELLED",
       "processing": "PUBLISHING", "uploading": "PUBLISHING", "pending": "SCHEDULED"}


def map_status(platform_status: str | None, post_status: str | None) -> str:
    if platform_status in MAP:
        return MAP[platform_status]
    if post_status in ("published", "failed"):
        return post_status.upper()
    return "SCHEDULED"


def apply_post(row, post: dict) -> None:
    """Copy status, URL and error from a Zernio post onto one Publication row."""
    for p in post.get("platforms", []):
        acc = p.get("accountId")
        acc = acc.get("_id") if isinstance(acc, dict) else acc  # string or populated object
        if str(acc) != row.account_id:
            continue
        row.status = map_status(p.get("status"), post.get("status"))
        row.post_url = p.get("platformPostUrl") or row.post_url
        row.error = p.get("errorMessage") if row.status == "FAILED" else None
        return
