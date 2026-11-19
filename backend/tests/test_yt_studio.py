from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import respx

import yt_studio
import youtube
from .test_youtube import client, connect_now  # noqa: F401  (shared fixtures)

G = "https://www.googleapis.com/youtube/v3"
TOK = "https://oauth2.googleapis.com/token"
INFO = "https://oauth2.googleapis.com/tokeninfo"
AN = "https://youtubeanalytics.googleapis.com/v2/reports"
SC = "https://www.googleapis.com/auth/"


def base(scopes=("youtube.upload", "youtube.readonly")):
    yt_studio._cache.clear()
    yt_studio._uploads.clear()
    respx.post(TOK).mock(return_value=httpx.Response(200, json={"access_token": "AT"}))
    respx.get(INFO).mock(return_value=httpx.Response(200, json={"scope": " ".join(SC + s for s in scopes)}))


CHANNEL = {"items": [{"id": "UC1", "snippet": {"title": "DGM GenMedia", "customUrl": "@dgmgenmedia", "publishedAt": "2026-01-01T00:00:00Z",
                                                "thumbnails": {"medium": {"url": "http://a/img.jpg"}}},
                      "statistics": {"viewCount": "120", "subscriberCount": "7", "videoCount": "3"},
                      "status": {"privacyStatus": "public", "isLinked": True, "longUploadsStatus": "allowed", "madeForKids": False},
                      "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}


@respx.mock
async def test_overview_and_access_show_real_permissions_and_roles(client):
    connect_now()
    base()
    respx.get(f"{G}/channels").mock(return_value=httpx.Response(200, json=CHANNEL))
    o = (await client.get("/api/youtube/studio/overview")).json()
    assert o["channel"]["title"] == "DGM GenMedia" and o["channel"]["subscribers"] == 7 and o["channel"]["long_uploads"] == "allowed"
    assert o["channel"]["links"]["analytics"].endswith("/channel/UC1/analytics") and o["reports_permission"] is False
    a = (await client.get("/api/youtube/studio/access")).json()
    granted = {s["name"]: s["granted"] for s in a["scopes"]}
    assert granted["Upload videos"] and granted["View your channel"] and not granted["View analytics reports"] and not granted["Manage your videos"]
    assert a["can_manage"] is False and a["roles"][0]["role"] == "Owner" and len(a["roles"]) == 7


@respx.mock
async def test_content_list_keeps_order_and_parses_stats(client):
    connect_now()
    base()
    respx.get(f"{G}/channels").mock(return_value=httpx.Response(200, json=CHANNEL))
    respx.get(f"{G}/playlistItems").mock(return_value=httpx.Response(200, json={
        "items": [{"contentDetails": {"videoId": "B"}}, {"contentDetails": {"videoId": "A"}}], "nextPageToken": "N2", "pageInfo": {"totalResults": 3}}))
    respx.get(f"{G}/videos").mock(return_value=httpx.Response(200, json={"items": [
        {"id": "A", "snippet": {"title": "Alpha", "publishedAt": "2026-02-01T00:00:00Z"}, "contentDetails": {"duration": "PT1M5S"},
         "statistics": {"viewCount": "10", "likeCount": "2", "commentCount": "1"}, "status": {"privacyStatus": "public"}},
        {"id": "B", "snippet": {"title": "Beta"}, "contentDetails": {"duration": "PT1H2M3S"}, "statistics": {},
         "status": {"privacyStatus": "private", "publishAt": "2030-01-01T00:00:00Z"}}]}))
    d = (await client.get("/api/youtube/studio/videos")).json()
    assert [v["id"] for v in d["items"]] == ["B", "A"] and d["next"] == "N2" and d["total"] == 3
    assert d["items"][0]["duration_s"] == 3723 and d["items"][0]["publish_at"] and d["items"][1]["views"] == 10
    assert d["items"][1]["studio_url"].endswith("/video/A/edit")


def analytics(request):
    q = dict(request.url.params)
    dims, start = q.get("dimensions", ""), q["startDate"]
    if dims == "":
        cur = start == (date.today() - timedelta(days=1) - timedelta(days=27)).isoformat()
        views = 100 if cur else 50
        return httpx.Response(200, json={"columnHeaders": [{"name": n} for n in ("views", "estimatedMinutesWatched", "subscribersGained", "subscribersLost", "likes", "comments", "shares", "averageViewDuration")],
                                         "rows": [[views, 600, 5, 1, 9, 2, 1, 42]]})
    heads = {"day": ["day", "views", "estimatedMinutesWatched", "subscribersGained", "subscribersLost", "likes", "comments", "shares"],
             "video": ["video", "views", "estimatedMinutesWatched", "likes"], "insightTrafficSourceType": ["insightTrafficSourceType", "views", "estimatedMinutesWatched"],
             "country": ["country", "views", "estimatedMinutesWatched"], "deviceType": ["deviceType", "views", "estimatedMinutesWatched"],
             "ageGroup,gender": ["ageGroup", "gender", "viewerPercentage"]}[dims]
    rows = {"day": [["2026-11-01", 10, 60, 1, 0, 2, 0, 0], ["2026-11-02", 20, 120, 0, 1, 3, 1, 1]], "video": [["V1", 80, 500, 7]],
            "insightTrafficSourceType": [["YT_SEARCH", 70, 400]], "country": [["AE", 90, 550]], "deviceType": [["MOBILE", 95, 580]],
            "ageGroup,gender": [["age25-34", "male", 41.5]]}[dims]
    return httpx.Response(200, json={"columnHeaders": [{"name": n} for n in heads], "rows": rows})


@respx.mock
async def test_reports_bundle_compares_with_the_previous_period_and_exports_csv(client):
    connect_now()
    base(("youtube.upload", "youtube.readonly", "yt-analytics.readonly"))
    respx.get(AN).mock(side_effect=analytics)
    respx.get(f"{G}/videos").mock(return_value=httpx.Response(200, json={"items": [{"id": "V1", "snippet": {"title": "Top one"}}]}))
    d = (await client.get("/api/youtube/studio/reports", params={"days": 28})).json()
    assert d["available"] and d["totals"]["views"] == 100 and d["previous"]["views"] == 50
    assert d["totals"]["netSubscribers"] == 4 and d["totals"]["watchHours"] == 10.0
    assert d["daily"][1]["netSubscribers"] == -1 and d["top_videos"][0]["title"] == "Top one"
    assert d["traffic"][0]["insightTrafficSourceType"] == "YT_SEARCH" and d["demographics"][0]["viewerPercentage"] == 41.5
    r = await client.get("/api/youtube/studio/reports.csv", params={"report": "daily", "days": 28})
    lines = r.text.strip().splitlines()
    assert r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    assert lines[0] == "day,views,watchHours,netSubscribers,likes,comments,shares" and lines[1].startswith("2026-11-01,10,")
    assert (await client.get("/api/youtube/studio/reports.csv", params={"report": "nope"})).status_code == 422


@respx.mock
async def test_reports_explain_what_is_missing(client):
    connect_now()
    base()
    respx.get(AN).mock(return_value=httpx.Response(403, json={"error": {"message": "Request had insufficient authentication scopes.", "errors": [{"reason": "insufficientPermissions"}]}}))
    d = (await client.get("/api/youtube/studio/reports")).json()
    assert d["available"] is False and d["problem"]["code"] == "scope"
    yt_studio._cache.clear()
    respx.get(AN).mock(return_value=httpx.Response(403, json={"error": {"message": "YouTube Analytics API has not been used in project 1 before or it is disabled.", "errors": [{"reason": "accessNotConfigured"}]}}))
    assert (await client.get("/api/youtube/studio/reports")).json()["problem"]["code"] == "api_disabled"


@respx.mock
async def test_playlists_and_a_clear_message_when_editing_needs_more_permission(client):
    connect_now()
    base()
    respx.get(f"{G}/playlists").mock(return_value=httpx.Response(200, json={"items": [
        {"id": "PL1", "snippet": {"title": "Water"}, "contentDetails": {"itemCount": 4}, "status": {"privacyStatus": "public"}}]}))
    assert (await client.get("/api/youtube/studio/playlists")).json()["items"][0] == {
        "id": "PL1", "title": "Water", "videos": 4, "privacy": "public", "created": None, "url": "https://www.youtube.com/playlist?list=PL1"}
    # videos.update refuses the upload-only permission: our app turns Google's answer into plain words
    row = await _row(client)
    respx.get(f"{G}/videos").mock(return_value=httpx.Response(200, json={"items": [{"snippet": {"title": "t", "categoryId": "22"}, "status": {"privacyStatus": "private"}}]}))
    respx.put(f"{G}/videos").mock(return_value=httpx.Response(403, json={"error": {"message": "Request had insufficient authentication scopes.", "errors": [{"reason": "insufficientPermissions"}]}}))
    r = await client.patch(f"/api/youtube/posts/{row}", json={"title": "New"})
    assert r.status_code == 403 and "add the missing permission" in r.json()["detail"]


async def _row(client):
    import io
    from .test_youtube import mock_upload, video
    mock_upload("VIDS")
    r = await client.post("/api/youtube/posts", files=video(), data={"title": "Old"})
    return r.json()["items"][0]["id"]


async def test_connect_link_can_ask_for_reports_and_manage_permissions(client):
    url = (await client.get("/api/youtube/connect", params={"reports": True, "manage": True})).json()["url"]
    scope = parse_qs(urlparse(url).query)["scope"][0]
    assert "yt-analytics.readonly" in scope and scope.endswith("/auth/youtube") and "youtube.upload" in scope
    plain = parse_qs(urlparse((await client.get("/api/youtube/connect")).json()["url"]).query)["scope"][0]
    assert "yt-analytics" not in plain and "include_granted_scopes" in (await client.get("/api/youtube/connect")).json()["url"]
