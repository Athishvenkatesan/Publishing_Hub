"""YouTube Studio management: channel, content, reports, playlists and the permissions this app holds (read-only)."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

import yt_studio
import youtube
from routes.youtube import select_account

router = APIRouter(prefix="/api/youtube/studio", dependencies=[Depends(select_account)])
G = "https://www.googleapis.com/auth/"
SCOPES = [
    (G + "youtube.upload", "Upload videos", "Upload videos and set a custom thumbnail.", "Needed"),
    (G + "youtube.readonly", "View your channel", "See your channel, videos, playlists and statistics.", "Needed"),
    (G + "yt-analytics.readonly", "View analytics reports", "Read the Reports tab: views, watch time, audience, traffic.", "Optional"),
    (G + "youtube", "Manage your videos", "Edit details, change visibility, reschedule and delete videos. Broad: it covers your whole YouTube account.", "Optional"),
    (G + "yt-analytics-monetary.readonly", "View revenue reports", "Revenue and ad reports. Only for monetized channels.", "Not requested"),
    (G + "youtube.force-ssl", "Manage comments and captions", "Read, reply to and delete comments. Very broad.", "Not requested"),
]
ROLES = [
    ("Owner", "Everything, including deleting the channel and managing permissions."),
    ("Manager", "Edit everything, publish and delete content, manage permissions. Cannot delete the channel."),
    ("Editor", "Edit everything and upload and publish. Cannot delete published content or manage permissions."),
    ("Editor (Limited)", "Same as Editor, without access to revenue data."),
    ("Subtitle Editor", "Add, edit, publish and delete subtitles on eligible videos only."),
    ("Viewer", "View channel details and revenue data. Cannot edit."),
    ("Viewer (Limited)", "Same as Viewer, without access to revenue data."),
]
CSV_REPORTS = {
    "daily": ("daily", ["day", "views", "watchHours", "netSubscribers", "likes", "comments", "shares"]),
    "videos": ("top_videos", ["video", "title", "views", "estimatedMinutesWatched", "likes"]),
    "traffic": ("traffic", ["insightTrafficSourceType", "views", "estimatedMinutesWatched"]),
    "countries": ("countries", ["country", "views", "estimatedMinutesWatched"]),
    "devices": ("devices", ["deviceType", "views", "estimatedMinutesWatched"]),
    "demographics": ("demographics", ["ageGroup", "gender", "viewerPercentage"]),
}


def _fail(e: youtube.YouTubeError):
    raise HTTPException(e.status, e.message)


@router.get("/overview")
async def overview():
    try:
        ch = await yt_studio.channel()
        granted = await yt_studio.scopes()
    except youtube.YouTubeError as e:
        _fail(e)
    return {"channel": ch, "reports_permission": youtube.ANALYTICS_SCOPE in granted}


@router.get("/videos")
async def videos(page_token: str = ""):
    try:
        return await yt_studio.videos(page_token)
    except youtube.YouTubeError as e:
        _fail(e)


@router.get("/videos.csv")
async def videos_csv():
    items, token = [], ""
    try:
        for _ in range(20):  # up to 1,000 videos, about 40 quota units
            page = await yt_studio.videos(token)
            items += page["items"]
            token = page["next"]
            if not token:
                break
    except youtube.YouTubeError as e:
        _fail(e)
    return _csv("youtube-content", ["id", "title", "privacy", "publish_at", "published_at", "duration_s", "views", "likes", "comments", "url"], items)


@router.get("/playlists")
async def playlists():
    try:
        return {"items": await yt_studio.playlists()}
    except youtube.YouTubeError as e:
        _fail(e)


@router.get("/access")
async def access():
    try:
        granted = set(await yt_studio.scopes())
        ch = await yt_studio.channel()
    except youtube.YouTubeError as e:
        _fail(e)
    return {"scopes": [{"scope": s, "name": n, "allows": a, "kind": k, "granted": s in granted} for s, n, a, k in SCOPES],
            "can_manage": youtube.MANAGE_SCOPE in granted, "can_report": youtube.ANALYTICS_SCOPE in granted,
            "channel": ch, "roles": [{"role": r, "can": c} for r, c in ROLES]}


@router.get("/reports")
async def reports(days: int = Query(28, ge=7, le=365)):
    try:
        return {"available": True, **await yt_studio.bundle(days)}
    except yt_studio.ReportsUnavailable as e:
        return {"available": False, "problem": {"code": e.code, "message": e.message}}
    except youtube.YouTubeError as e:
        _fail(e)


def _csv(name: str, cols: list[str], rows: list[dict]) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c, "") for c in cols])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})


@router.get("/reports.csv")
async def reports_csv(report: str, days: int = Query(28, ge=7, le=365)):
    if report not in CSV_REPORTS:
        raise HTTPException(422, "Unknown report")
    try:
        data = await yt_studio.bundle(days)
    except yt_studio.ReportsUnavailable as e:
        raise HTTPException(403, e.message)
    except youtube.YouTubeError as e:
        _fail(e)
    key, cols = CSV_REPORTS[report]
    return _csv(f"youtube-{report}-{data['range']['start']}-to-{data['range']['end']}", cols, data[key])
