import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import db
import models  # noqa: F401
from config import settings
from db import Base

G = "https://graph.facebook.com/v21.0"
V = "https://graph-video.facebook.com/v21.0"


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "meta_access_token", "TESTTOKEN")
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    db.engine, db.SessionLocal = eng, async_sessionmaker(eng, expire_on_commit=False)
    async with eng.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    import app as appmod

    async def sess():
        async with db.SessionLocal() as s:
            yield s
    appmod.app.dependency_overrides[db.get_session] = sess
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        yield c


def fb_upload(vid):
    """Fake Meta resumable upload: start, one transfer, finish."""
    def answer(request):
        body = request.content
        if b"upload_phase=start" in body:
            return httpx.Response(200, json={"video_id": vid, "upload_session_id": "S1", "start_offset": "0", "end_offset": "2048"})
        if b"transfer" in body:
            return httpx.Response(200, json={"start_offset": "2048", "end_offset": "2048"})
        return httpx.Response(200, json={"success": True})
    return answer


def video():
    return {"file": ("clip.mp4", io.BytesIO(b"x" * 2048), "video/mp4")}


@respx.mock
async def test_check_lists_pages_and_capabilities_without_leaking_tokens(client):
    respx.get(f"{G}/me").mock(return_value=httpx.Response(200, json={"id": "1", "name": "Athish"}))
    respx.get(f"{G}/me/permissions").mock(return_value=httpx.Response(200, json={"data": [
        {"permission": "pages_manage_posts", "status": "granted"}, {"permission": "email", "status": "declined"}]}))
    respx.get(f"{G}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [
        {"id": "P1", "name": "My Page", "tasks": ["CREATE_CONTENT"], "access_token": "SECRETPAGETOKEN"}]}))
    r = await client.get("/api/facebook/check")
    assert r.status_code == 200, r.text
    d = r.json()
    caps = {c["key"]: c["ok"] for c in d["capabilities"]}
    assert caps == {"facebook_video": True, "instagram_video": False, "threads_video": False, "whatsapp_message": False}
    assert d["pages"][0]["name"] == "My Page" and "SECRETPAGETOKEN" not in r.text and "TESTTOKEN" not in r.text


@respx.mock
async def test_expired_token_gives_a_clear_message(client):
    respx.get(f"{G}/me").mock(return_value=httpx.Response(400, json={"error": {"code": 190, "message": "Session has expired"}}))
    r = await client.get("/api/facebook/check")
    assert r.status_code == 401 and "expired" in r.json()["detail"]


@respx.mock
async def test_publish_now_then_status_becomes_published(client):
    respx.get(f"{G}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [{"id": "P1", "name": "My Page", "access_token": "PT"}]}))
    route = respx.post(f"{V}/P1/videos").mock(side_effect=fb_upload("V9"))
    r = await client.post("/api/facebook/posts", files=video(), data={"page_id": "P1", "title": "T", "description": "D", "mode": "now"})
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["status"] == "PUBLISHING"
    assert len(route.calls) == 3 and b"video_file_chunk" in route.calls[1].request.content
    body = route.calls[-1].request.content
    assert b"published" not in body and b"title=T" in body
    respx.get(f"{G}/V9").mock(return_value=httpx.Response(200, json={
        "status": {"video_status": "ready"}, "permalink_url": "/MyPage/videos/9", "published": True}))
    h = (await client.get("/api/facebook/posts")).json()["items"][0]
    assert h["status"] == "PUBLISHED" and h["post_url"] == "https://www.facebook.com/MyPage/videos/9"


@respx.mock
async def test_schedule_sends_unix_time_and_rejects_bad_times(client):
    respx.get(f"{G}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [{"id": "P1", "name": "My Page", "access_token": "PT"}]}))
    route = respx.post(f"{V}/P1/videos").mock(side_effect=fb_upload("V10"))
    soon = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(minutes=3)).strftime("%Y-%m-%dT%H:%M")
    r = await client.post("/api/facebook/posts", files=video(), data={"page_id": "P1", "mode": "schedule", "scheduled_at": soon, "tz": "Asia/Dubai"})
    assert r.status_code == 422 and "10 minutes" in r.json()["detail"]
    later = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    r = await client.post("/api/facebook/posts", files=video(), data={"page_id": "P1", "mode": "schedule", "scheduled_at": later, "tz": "Asia/Dubai"})
    assert r.status_code == 200, r.text
    body = route.calls[-1].request.content
    assert b"scheduled_publish_time" in body and b"SCHEDULED" in body
    assert r.json()["items"][0]["status"] == "SCHEDULED"


def image(name="pic.jpg"):
    return {"file": (name, io.BytesIO(b"x" * 1024), "image/jpeg")}


@respx.mock
async def test_photo_publish_now_returns_link(client):
    respx.get(f"{G}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [{"id": "P1", "name": "My Page", "access_token": "PT"}]}))
    route = respx.post(f"{G}/P1/photos").mock(return_value=httpx.Response(200, json={"id": "PH1", "post_id": "P1_55"}))
    r = await client.post("/api/facebook/photos", files=image(), data={"page_id": "P1", "caption": "hello #a", "mode": "now"})
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["status"] == "PUBLISHED" and item["post_url"] == "https://www.facebook.com/P1_55"
    body = route.calls[0].request.content
    assert b'name="caption"' in body and b"scheduled_publish_time" not in body
    assert (await client.get("/api/facebook/posts")).json()["items"][0]["filename"] == "pic.jpg"


@respx.mock
async def test_photo_schedule_and_rejects_non_image(client):
    respx.get(f"{G}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [{"id": "P1", "name": "My Page", "access_token": "PT"}]}))
    route = respx.post(f"{G}/P1/photos").mock(return_value=httpx.Response(200, json={"id": "PH2"}))
    later = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    r = await client.post("/api/facebook/photos", files=image(), data={"page_id": "P1", "mode": "schedule", "scheduled_at": later, "tz": "Asia/Dubai"})
    assert r.status_code == 200 and r.json()["items"][0]["status"] == "SCHEDULED"
    assert b"scheduled_publish_time" in route.calls[0].request.content
    r = await client.post("/api/facebook/photos", files={"file": ("a.mp4", io.BytesIO(b"x"), "video/mp4")}, data={"page_id": "P1"})
    assert r.status_code == 422


@respx.mock
async def test_multi_posts_to_each_page_and_reports_failures(client):
    respx.get(f"{G}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [{"id": "P1", "name": "My Page", "access_token": "PT"}]}))
    respx.post(f"{V}/P1/videos").mock(side_effect=fb_upload("V1"))
    r = await client.post("/api/facebook/posts/multi", files=video(), data={"pages": ["P1", "P2"], "title": "T", "description": "D", "mode": "now"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert [i["account_name"] for i in d["items"]] == ["My Page"]
    assert d["errors"][0]["key"] == "P2" and "cannot post" in d["errors"][0]["error"]


async def test_multi_rejects_a_non_video(client):
    r = await client.post("/api/facebook/posts/multi", files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")}, data={"pages": ["P1"]})
    assert r.status_code == 422


@respx.mock
async def test_missing_post_permission_says_what_to_add(client):
    respx.get(f"{G}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [{"id": "P1", "name": "My Page", "access_token": "PT"}]}))
    respx.post(f"{V}/P1/videos").mock(return_value=httpx.Response(400, json={"error": {"code": 100, "message": "(#100) No permission to publish the video"}}))
    d = (await client.post("/api/facebook/posts/multi", files=video(), data={"pages": ["P1"], "title": "T"})).json()
    assert not d["items"] and "pages_manage_posts" in d["errors"][0]["error"]


def ig_linked():
    respx.get(f"{G}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [
        {"id": "P1", "name": "My Page", "access_token": "PT", "instagram_business_account": {"id": "IG1", "username": "dgm"}}]}))


@respx.mock
async def test_instagram_reel_upload_waits_then_publishes(client, monkeypatch):
    monkeypatch.setattr("meta_ig.POLL", 0)
    ig_linked()
    make = respx.post(f"{G}/IG1/media").mock(return_value=httpx.Response(200, json={"id": "C1", "uri": "https://rupload.facebook.com/ig-api-upload/v21.0/C1"}))
    up = respx.post("https://rupload.facebook.com/ig-api-upload/v21.0/C1").mock(return_value=httpx.Response(200, json={"success": True}))
    respx.get(f"{G}/C1").mock(side_effect=[httpx.Response(200, json={"status_code": "IN_PROGRESS"}), httpx.Response(200, json={"status_code": "FINISHED"})])
    pub = respx.post(f"{G}/IG1/media_publish").mock(return_value=httpx.Response(200, json={"id": "M1"}))
    respx.get(f"{G}/M1").mock(return_value=httpx.Response(200, json={"permalink": "https://www.instagram.com/reel/abc/"}))
    r = await client.post("/api/facebook/posts/multi", files=video(), data={"instagram": ["IG1"], "caption": "Hi #A", "description": "long"})
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["platform"] == "instagram-meta" and item["post_url"] == "https://www.instagram.com/reel/abc/" and item["status"] == "PUBLISHED"
    assert b"REELS" in make.calls[0].request.content and b"caption=Hi" in make.calls[0].request.content
    assert up.calls[0].request.headers["file_size"] == "2048" and up.calls[0].request.headers["authorization"].startswith("OAuth ")
    assert b"creation_id=C1" in pub.calls[0].request.content
    h = (await client.get("/api/facebook/posts")).json()["items"]
    assert h[0]["account_name"] == "dgm"


async def test_instagram_cannot_be_scheduled_and_needs_a_target(client):
    later = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    r = await client.post("/api/facebook/posts/multi", files=video(), data={"instagram": ["IG1"], "mode": "schedule", "scheduled_at": later})
    assert r.status_code == 422 and "right away" in r.json()["detail"]
    r = await client.post("/api/facebook/posts/multi", files=video(), data={"title": "T"})
    assert r.status_code == 422 and "Tick" in r.json()["detail"]


@respx.mock
async def test_instagram_not_linked_is_reported_and_others_still_post(client):
    ig_linked()
    respx.post(f"{V}/P1/videos").mock(side_effect=fb_upload("V1"))
    d = (await client.post("/api/facebook/posts/multi", files=video(), data={"pages": ["P1"], "instagram": ["IG9"]})).json()
    assert [i["platform"] for i in d["items"]] == ["facebook"] and "not linked" in d["errors"][0]["error"]


TH = "https://graph.threads.net/v1.0"


def ig_reel_ok():
    respx.post(f"{G}/IG1/media").mock(return_value=httpx.Response(200, json={"id": "C1", "uri": "https://rupload.facebook.com/ig-api-upload/v21.0/C1"}))
    respx.post("https://rupload.facebook.com/ig-api-upload/v21.0/C1").mock(return_value=httpx.Response(200, json={"success": True}))
    respx.get(f"{G}/C1").mock(return_value=httpx.Response(200, json={"status_code": "FINISHED"}))
    respx.post(f"{G}/IG1/media_publish").mock(return_value=httpx.Response(200, json={"id": "M1"}))
    respx.get(f"{G}/M1").mock(return_value=httpx.Response(200, json={"permalink": "https://www.instagram.com/reel/abc/", "media_url": "https://cdn.example/v.mp4"}))


@respx.mock
async def test_threads_posts_the_instagram_copy(client, monkeypatch):
    monkeypatch.setattr(settings, "threads_access_token", "THTOKEN")
    monkeypatch.setattr("meta_threads.POLL", 0)
    ig_linked(); ig_reel_ok()
    start = respx.post(f"{TH}/me/threads").mock(return_value=httpx.Response(200, json={"id": "TC1"}))
    respx.get(f"{TH}/TC1").mock(side_effect=[httpx.Response(200, json={"status": "IN_PROGRESS"}), httpx.Response(200, json={"status": "FINISHED"})])
    respx.post(f"{TH}/me/threads_publish").mock(return_value=httpx.Response(200, json={"id": "T9"}))
    respx.get(f"{TH}/T9").mock(return_value=httpx.Response(200, json={"permalink": "https://www.threads.net/@dgm/post/x", "username": "dgm"}))
    d = (await client.post("/api/facebook/posts/multi", files=video(), data={"instagram": ["IG1"], "threads": "true", "caption": "Hi #A"})).json()
    assert [i["platform"] for i in d["items"]] == ["instagram-meta", "threads"], d
    assert d["items"][1]["post_url"] == "https://www.threads.net/@dgm/post/x"
    body = start.calls[0].request.content
    assert b"video_url=https%3A%2F%2Fcdn.example%2Fv.mp4" in body and b"media_type=VIDEO" in body and b"THTOKEN" in body


@respx.mock
async def test_threads_without_its_token_fails_alone(client, monkeypatch):
    monkeypatch.setattr(settings, "threads_access_token", "")
    monkeypatch.setattr("meta._fresh_env", lambda: None)
    ig_linked(); ig_reel_ok()
    d = (await client.post("/api/facebook/posts/multi", files=video(), data={"instagram": ["IG1"], "threads": "true", "caption": "Hi"})).json()
    assert [i["platform"] for i in d["items"]] == ["instagram-meta"] and "THREADS_ACCESS_TOKEN" in d["errors"][0]["error"]


async def test_threads_alone_is_refused(client):
    r = await client.post("/api/facebook/posts/multi", files=video(), data={"threads": "true"})
    assert r.status_code == 422 and "Threads needs Instagram or Facebook" in r.json()["detail"]
