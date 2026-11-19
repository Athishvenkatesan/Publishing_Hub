import json

import httpx
import respx

import youtube
from .test_youtube import client, connect_now, mock_upload, video  # noqa: F401  (shared fixtures)

VID = "https://www.googleapis.com/youtube/v3/videos"
TOK = "https://oauth2.googleapis.com/token"
CURRENT = {"items": [{"snippet": {"title": "Old", "description": "Old text", "tags": ["a", "b"], "categoryId": "22", "defaultLanguage": "en", "channelId": "x"},
                      "status": {"privacyStatus": "private", "publishAt": "2030-01-01T00:00:00Z", "license": "youtube", "embeddable": True,
                                 "publicStatsViewable": True, "selfDeclaredMadeForKids": False, "uploadStatus": "processed"}}]}


async def make_row(client):
    connect_now()
    mock_upload("VIDX")
    r = await client.post("/api/youtube/posts", files=video(), data={"title": "Old", "description": "Old text"})
    return r.json()["items"][0]["id"]


@respx.mock
async def test_edit_keeps_everything_it_was_not_asked_to_change(client):
    rid = await make_row(client)
    respx.get(VID).mock(return_value=httpx.Response(200, json=CURRENT))
    put = respx.put(VID).mock(return_value=httpx.Response(200, json={}))
    r = await client.patch(f"/api/youtube/posts/{rid}", json={"title": "  New title  "})
    assert r.status_code == 200, r.text
    sent = json.loads(put.calls[0].request.content)
    assert sent["id"] == "VIDX" and sent["snippet"]["title"] == "New title"
    assert sent["snippet"]["description"] == "Old text" and sent["snippet"]["tags"] == ["a", "b"] and sent["snippet"]["categoryId"] == "22"
    assert "channelId" not in sent["snippet"] and "uploadStatus" not in sent["status"] and sent["status"]["publishAt"] == "2030-01-01T00:00:00Z"
    assert r.json()["item"]["title"] == "New title"
    bad = await client.patch(f"/api/youtube/posts/{rid}", json={"title": "   "})
    assert bad.status_code == 422


@respx.mock
async def test_visibility_and_cancel_schedule_drop_the_publish_time(client):
    rid = await make_row(client)
    respx.get(VID).mock(return_value=httpx.Response(200, json=CURRENT))
    put = respx.put(VID).mock(return_value=httpx.Response(200, json={}))
    r = await client.patch(f"/api/youtube/posts/{rid}", json={"cancel_schedule": True})
    st = json.loads(put.calls[0].request.content)["status"]
    assert st["privacyStatus"] == "private" and "publishAt" not in st
    assert r.json()["item"]["status"] == "PUBLISHED"
    await client.patch(f"/api/youtube/posts/{rid}", json={"privacy": "unlisted"})
    assert json.loads(put.calls[1].request.content)["status"]["privacyStatus"] == "unlisted"
    assert (await client.patch(f"/api/youtube/posts/{rid}", json={"privacy": "secret"})).status_code == 422


@respx.mock
async def test_reschedule_sets_private_with_a_new_publish_time(client):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    rid = await make_row(client)
    respx.get(VID).mock(return_value=httpx.Response(200, json=CURRENT))
    put = respx.put(VID).mock(return_value=httpx.Response(200, json={}))
    soon = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M")
    assert (await client.patch(f"/api/youtube/posts/{rid}", json={"scheduled_at": soon, "tz": "Asia/Dubai"})).status_code == 422
    later = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    r = await client.patch(f"/api/youtube/posts/{rid}", json={"scheduled_at": later, "tz": "Asia/Dubai"})
    assert r.status_code == 200, r.text
    st = json.loads(put.calls[0].request.content)["status"]
    assert st["privacyStatus"] == "private" and st["publishAt"].endswith("Z")
    assert r.json()["item"]["status"] == "SCHEDULED" and r.json()["item"]["mode"] == "schedule"


@respx.mock
async def test_details_delete_and_remove_from_list(client):
    rid = await make_row(client)
    respx.get(VID).mock(return_value=httpx.Response(200, json=CURRENT))
    d = (await client.get(f"/api/youtube/posts/{rid}/details")).json()
    assert d["title"] == "Old" and d["tags"] == "a, b" and d["privacy"] == "private"
    gone = respx.delete(VID).mock(return_value=httpx.Response(204))
    rid2 = await make_row(client)
    assert (await client.delete(f"/api/youtube/posts/{rid2}/local")).json() == {"ok": True}
    assert gone.call_count == 0  # removing from the list never touches YouTube
    assert (await client.delete(f"/api/youtube/posts/{rid}")).json() == {"ok": True}
    assert gone.call_count == 1 and gone.calls[0].request.url.params["id"] == "VIDX"
    assert (await client.delete(f"/api/youtube/posts/{rid}")).status_code == 404
