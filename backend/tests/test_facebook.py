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
    assert caps == {"facebook_video": True, "instagram_video": False, "whatsapp_message": False}
    assert d["pages"][0]["name"] == "My Page" and "SECRETPAGETOKEN" not in r.text and "TESTTOKEN" not in r.text


@respx.mock
async def test_expired_token_gives_a_clear_message(client):
    respx.get(f"{G}/me").mock(return_value=httpx.Response(400, json={"error": {"code": 190, "message": "Session has expired"}}))
    r = await client.get("/api/facebook/check")
    assert r.status_code == 401 and "expired" in r.json()["detail"]


@respx.mock
async def test_publish_now_then_status_becomes_published(client):
    respx.get(f"{G}/P1").mock(return_value=httpx.Response(200, json={"name": "My Page", "access_token": "PT"}))
    route = respx.post(f"{V}/P1/videos").mock(return_value=httpx.Response(200, json={"id": "V9"}))
    r = await client.post("/api/facebook/posts", files=video(), data={"page_id": "P1", "title": "T", "description": "D", "mode": "now"})
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["status"] == "PUBLISHING"
    body = route.calls[0].request.content
    assert b"published" not in body and b'name="title"' in body
    respx.get(f"{G}/V9").mock(return_value=httpx.Response(200, json={
        "status": {"video_status": "ready"}, "permalink_url": "/MyPage/videos/9", "published": True}))
    h = (await client.get("/api/facebook/posts")).json()["items"][0]
    assert h["status"] == "PUBLISHED" and h["post_url"] == "https://www.facebook.com/MyPage/videos/9"


@respx.mock
async def test_schedule_sends_unix_time_and_rejects_bad_times(client):
    respx.get(f"{G}/P1").mock(return_value=httpx.Response(200, json={"name": "My Page", "access_token": "PT"}))
    route = respx.post(f"{V}/P1/videos").mock(return_value=httpx.Response(200, json={"id": "V10"}))
    soon = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(minutes=3)).strftime("%Y-%m-%dT%H:%M")
    r = await client.post("/api/facebook/posts", files=video(), data={"page_id": "P1", "mode": "schedule", "scheduled_at": soon, "tz": "Asia/Dubai"})
    assert r.status_code == 422 and "10 minutes" in r.json()["detail"]
    later = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    r = await client.post("/api/facebook/posts", files=video(), data={"page_id": "P1", "mode": "schedule", "scheduled_at": later, "tz": "Asia/Dubai"})
    assert r.status_code == 200, r.text
    body = route.calls[0].request.content
    assert b"scheduled_publish_time" in body and b"SCHEDULED" in body
    assert r.json()["items"][0]["status"] == "SCHEDULED"
