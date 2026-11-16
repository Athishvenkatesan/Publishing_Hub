import io
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

import db
import models  # noqa: F401  (register tables before create_all)
from db import Base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

Z = "https://zernio.com/api/v1"
ACC = {"accounts": [{"_id": "acc1", "platform": "instagram", "username": "aivideo.3321", "isActive": True}]}


@pytest.fixture
async def client(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    db.engine, db.SessionLocal = eng, async_sessionmaker(eng, expire_on_commit=False)
    async with eng.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    import app as appmod
    appmod.app.dependency_overrides[db.get_session] = lambda: None
    async def sess():
        async with db.SessionLocal() as s:
            yield s
    appmod.app.dependency_overrides[db.get_session] = sess
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        yield c


def mock_zernio(post):
    respx.get(f"{Z}/accounts").mock(return_value=httpx.Response(200, json=ACC))
    respx.post(f"{Z}/media/presign").mock(return_value=httpx.Response(200, json={
        "uploadUrl": "https://up.test/put", "publicUrl": "https://media.zernio.com/v.mp4"}))
    respx.put("https://up.test/put").mock(return_value=httpx.Response(200))
    return respx.post(f"{Z}/posts").mock(return_value=httpx.Response(201, json={"post": post}))


def video():
    return {"file": ("clip.mp4", io.BytesIO(b"x" * 2048), "video/mp4")}


@respx.mock
async def test_publish_now_shows_published_with_link(client):
    route = mock_zernio({"_id": "p1", "status": "published", "platforms": [
        {"platform": "instagram", "accountId": "acc1", "status": "published", "platformPostUrl": "https://instagram.com/reel/abc"}]})
    r = await client.post("/api/posts", files=video(), data={"texts": json.dumps({"instagram": {"caption": "hi #a"}}), "account_ids": ["acc1"], "mode": "now"})
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["status"] == "PUBLISHED" and item["post_url"].endswith("/abc")
    sent = json.loads(route.calls[0].request.content)
    assert sent["publishNow"] is True and sent["mediaItems"][0]["type"] == "video"
    assert (await client.get("/api/posts")).json()["items"][0]["status"] == "PUBLISHED"


@respx.mock
async def test_schedule_sends_local_time_and_zone_then_status_updates(client):
    when = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    route = mock_zernio({"_id": "p2", "status": "scheduled", "platforms": [
        {"platform": "instagram", "accountId": "acc1", "status": "pending"}]})
    r = await client.post("/api/posts", files=video(), data={
        "account_ids": ["acc1"], "mode": "schedule", "scheduled_at": when, "tz": "Asia/Dubai"})
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["status"] == "SCHEDULED"
    sent = json.loads(route.calls[0].request.content)
    assert sent["scheduledFor"] == when and sent["timezone"] == "Asia/Dubai" and "publishNow" not in sent
    respx.get(f"{Z}/posts/p2").mock(return_value=httpx.Response(200, json={"post": {
        "_id": "p2", "status": "published", "platforms": [
            {"platform": "instagram", "accountId": "acc1", "status": "published", "platformPostUrl": "https://instagram.com/reel/zzz"}]}}))
    h = (await client.get("/api/posts")).json()["items"][0]
    assert h["status"] == "PUBLISHED" and h["post_url"].endswith("/zzz")


@respx.mock
async def test_failure_is_recorded_with_reason(client):
    mock_zernio({"_id": "p3", "status": "failed", "platforms": [
        {"platform": "instagram", "accountId": "acc1", "status": "failed", "errorMessage": "Media too long"}]})
    r = await client.post("/api/posts", files=video(), data={"account_ids": ["acc1"], "mode": "now"})
    item = r.json()["items"][0]
    assert item["status"] == "FAILED" and item["error"] == "Media too long"


async def test_rejects_past_time_and_bad_file(client):
    r = await client.post("/api/posts", files=video(), data={
        "account_ids": ["acc1"], "mode": "schedule", "scheduled_at": "2020-01-01T10:00", "tz": "Asia/Dubai"})
    assert r.status_code == 422
    r = await client.post("/api/posts", files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")},
                          data={"account_ids": ["acc1"], "mode": "now"})
    assert r.status_code == 422


YT = {"accounts": [{"_id": "yt1", "platform": "youtube", "username": "chan", "isActive": True}]}


@respx.mock
async def test_youtube_needs_title_and_sends_per_platform_copy(client):
    route = mock_zernio({"_id": "p9", "status": "scheduled", "platforms": [
        {"platform": "instagram", "accountId": "acc1", "status": "pending"},
        {"platform": "youtube", "accountId": "yt1", "status": "pending"}]})
    respx.get(f"{Z}/accounts").mock(return_value=httpx.Response(200, json={"accounts": ACC["accounts"] + YT["accounts"]}))
    when = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    base = {"account_ids": ["acc1", "yt1"], "mode": "schedule", "scheduled_at": when, "tz": "Asia/Dubai"}
    r = await client.post("/api/posts", files=video(), data={**base, "texts": json.dumps({"instagram": {"caption": "x"}, "youtube": {"title": ""}})})
    assert r.status_code == 422 and "title" in r.json()["detail"]
    copy = {"instagram": {"caption": "ig text #a #b"},
            "youtube": {"title": "My title", "caption": "yt description", "tags": ["a", "b"]}}
    r = await client.post("/api/posts", files=video(), data={**base, "texts": json.dumps(copy)})
    assert r.status_code == 200, r.text
    sent = json.loads(route.calls[-1].request.content)
    by = {p["platform"]: p for p in sent["platforms"]}
    assert by["instagram"]["customContent"] == "ig text #a #b"
    assert by["youtube"]["customContent"] == "yt description"
    assert by["youtube"]["platformSpecificData"]["title"] == "My title"
    assert sent["tags"] == ["a", "b"]


@respx.mock
async def test_connect_link_and_disconnect(client):
    respx.get(f"{Z}/profiles").mock(return_value=httpx.Response(200, json={"profiles": [{"_id": "pr1", "isDefault": True}]}))
    route = respx.get(f"{Z}/connect/instagram").mock(return_value=httpx.Response(200, json={"authUrl": "https://auth.test/x"}))
    r = await client.post("/api/accounts/connect", json={"platform": "instagram", "return_to": "http://localhost:3100/"})
    assert r.json()["url"] == "https://auth.test/x"
    assert route.calls[0].request.url.params["profileId"] == "pr1"
    assert (await client.post("/api/accounts/connect", json={"platform": "bad", "return_to": "x"})).status_code == 422
    respx.delete(f"{Z}/accounts/acc1").mock(return_value=httpx.Response(200, json={}))
    assert (await client.delete("/api/accounts/acc1")).json() == {"ok": True}
