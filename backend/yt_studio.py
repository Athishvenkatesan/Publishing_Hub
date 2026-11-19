"""Read-only YouTube data for the Studio screen: channel, videos, playlists, the permissions this app holds, and Analytics reports.
Nothing here changes anything on the channel."""
import asyncio
import re
import time
from datetime import date, timedelta

import httpx

import yt_accounts
import youtube
from youtube import ANALYTICS_SCOPE, API, YouTubeError, _access_token, _raise

ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"
STUDIO = "https://studio.youtube.com"
BASE_METRICS = "views,estimatedMinutesWatched,subscribersGained,subscribersLost,likes,comments,shares"
CACHE_S = 300
_cache: dict = {}
_uploads: dict = {}


class ReportsUnavailable(Exception):
    """The reports need something the user must switch on. code: scope | api_disabled."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


async def _get(url: str, params: dict) -> dict:
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, params=params, headers={"Authorization": f"Bearer {tok}"})
    _raise(r)
    return r.json()


async def scopes() -> list[str]:
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(TOKENINFO, params={"access_token": tok})
    _raise(r)
    return sorted(r.json().get("scope", "").split())


def _num(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


async def channel() -> dict | None:
    d = await _get(f"{API}/channels", {"part": "snippet,statistics,status,brandingSettings,contentDetails", "mine": "true"})
    items = d.get("items", [])
    if not items:
        return None
    c = items[0]
    sn, st, stat = c["snippet"], c.get("status", {}), c.get("statistics", {})
    _uploads[yt_accounts.current().key] = c.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    return {"id": c["id"], "title": sn["title"], "handle": sn.get("customUrl", ""), "description": sn.get("description", ""),
            "created": sn.get("publishedAt"), "country": sn.get("country", ""), "avatar": (sn.get("thumbnails", {}).get("medium") or {}).get("url"),
            "keywords": c.get("brandingSettings", {}).get("channel", {}).get("keywords", ""),
            "views": _num(stat.get("viewCount")), "subscribers": None if stat.get("hiddenSubscriberCount") else _num(stat.get("subscriberCount")),
            "videos": _num(stat.get("videoCount")), "privacy": st.get("privacyStatus"), "is_linked": st.get("isLinked"),
            "long_uploads": st.get("longUploadsStatus"), "made_for_kids": st.get("madeForKids"),
            "links": {k: f"{STUDIO}/channel/{c['id']}{v}" for k, v in {"dashboard": "", "content": "/videos", "analytics": "/analytics",
                                                                      "comments": "/comments", "playlists": "/playlists"}.items()}}


def _seconds(iso: str) -> int:
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0) if m else 0


def _video(v: dict) -> dict:
    sn, st, stat = v["snippet"], v.get("status", {}), v.get("statistics", {})
    return {"id": v["id"], "title": sn["title"], "thumb": (sn.get("thumbnails", {}).get("medium") or sn.get("thumbnails", {}).get("default") or {}).get("url"),
            "published_at": sn.get("publishedAt"), "duration_s": _seconds(v.get("contentDetails", {}).get("duration", "")),
            "privacy": st.get("privacyStatus"), "publish_at": st.get("publishAt"), "made_for_kids": st.get("madeForKids"),
            "views": _num(stat.get("viewCount")), "likes": _num(stat.get("likeCount")), "comments": _num(stat.get("commentCount")),
            "url": f"https://www.youtube.com/watch?v={v['id']}", "studio_url": f"{STUDIO}/video/{v['id']}/edit"}


async def videos(page_token: str = "") -> dict:
    """One page (up to 50) of uploads, newest first, with stats. Costs about 2 quota units."""
    acct = yt_accounts.current().key
    if not _uploads.get(acct):
        await channel()
    if not _uploads.get(acct):
        return {"items": [], "next": None, "total": 0}
    page = await _get(f"{API}/playlistItems", {"part": "contentDetails", "playlistId": _uploads[acct], "maxResults": 50, "pageToken": page_token})
    ids = [i["contentDetails"]["videoId"] for i in page.get("items", [])]
    if not ids:
        return {"items": [], "next": None, "total": page.get("pageInfo", {}).get("totalResults", 0)}
    d = await _get(f"{API}/videos", {"part": "snippet,statistics,status,contentDetails", "id": ",".join(ids)})
    by_id = {v["id"]: _video(v) for v in d.get("items", [])}
    return {"items": [by_id[i] for i in ids if i in by_id], "next": page.get("nextPageToken"), "total": page.get("pageInfo", {}).get("totalResults", 0)}


async def playlists() -> list[dict]:
    out, token = [], ""
    for _ in range(4):
        d = await _get(f"{API}/playlists", {"part": "snippet,contentDetails,status", "mine": "true", "maxResults": 50, "pageToken": token})
        for p in d.get("items", []):
            out.append({"id": p["id"], "title": p["snippet"]["title"], "videos": p.get("contentDetails", {}).get("itemCount", 0),
                        "privacy": p.get("status", {}).get("privacyStatus"), "created": p["snippet"].get("publishedAt"),
                        "url": f"https://www.youtube.com/playlist?list={p['id']}"})
        token = d.get("nextPageToken", "")
        if not token:
            break
    return out


# ---------------- Analytics reports ----------------
async def report(start: date, end: date, metrics: str, dimensions: str = "", sort: str = "", limit: int | None = None) -> list[dict]:
    params = {"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(), "metrics": metrics}
    if dimensions:
        params["dimensions"] = dimensions
    if sort:
        params["sort"] = sort
    if limit:
        params["maxResults"] = limit
    tok = await _access_token()
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.get(ANALYTICS, params=params, headers={"Authorization": f"Bearer {tok}"})
    if r.status_code in (401, 403):
        text = r.text.lower()
        if "accessnotconfigured" in text or "has not been used" in text or "is disabled" in text:
            raise ReportsUnavailable("api_disabled", "The YouTube Analytics API is not switched on in your Google Cloud project.")
        raise ReportsUnavailable("scope", "Reports need one more permission from your Google account.")
    _raise(r)
    d = r.json()
    names = [h["name"] for h in d.get("columnHeaders", [])]
    return [dict(zip(names, row)) for row in d.get("rows", [])]


async def _video_titles(ids: list[str]) -> dict:
    if not ids:
        return {}
    d = await _get(f"{API}/videos", {"part": "snippet", "id": ",".join(ids)})
    return {v["id"]: v["snippet"]["title"] for v in d.get("items", [])}


def _sum(row: dict) -> dict:
    row = dict(row)
    row["netSubscribers"] = _num(row.get("subscribersGained")) - _num(row.get("subscribersLost"))
    row["watchHours"] = round(float(row.get("estimatedMinutesWatched") or 0) / 60, 1)
    return row


async def bundle(days: int) -> dict:
    """Everything the Reports tab shows, for the last `days` full days. Cached for a few minutes."""
    key = (yt_accounts.current().key, days)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    end = date.today() - timedelta(days=1)  # the newest days are often not ready yet
    start = end - timedelta(days=days - 1)
    p_end = start - timedelta(days=1)
    p_start = p_end - timedelta(days=days - 1)
    tot, prev, daily, top, traffic, countries, devices, demo = await asyncio.gather(
        report(start, end, BASE_METRICS + ",averageViewDuration"), report(p_start, p_end, BASE_METRICS + ",averageViewDuration"),
        report(start, end, BASE_METRICS, "day", "day"), report(start, end, "views,estimatedMinutesWatched,likes", "video", "-views", 10),
        report(start, end, "views,estimatedMinutesWatched", "insightTrafficSourceType", "-views"),
        report(start, end, "views,estimatedMinutesWatched", "country", "-views", 10),
        report(start, end, "views,estimatedMinutesWatched", "deviceType", "-views"), report(start, end, "viewerPercentage", "ageGroup,gender"))
    titles = await _video_titles([t["video"] for t in top])
    out = {"range": {"start": start.isoformat(), "end": end.isoformat(), "days": days},
           "totals": _sum(tot[0]) if tot else {}, "previous": _sum(prev[0]) if prev else {},
           "daily": [_sum(r) for r in daily],
           "top_videos": [{**t, "title": titles.get(t["video"], t["video"])} for t in top],
           "traffic": traffic, "countries": countries, "devices": devices, "demographics": demo}
    _cache[key] = (time.time(), out)
    return out
