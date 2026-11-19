import io
import json
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import db
import models  # noqa: F401
import youtube
from config import settings
from db import Base

TOK = "https://oauth2.googleapis.com/token"
VID = "https://www.googleapis.com/youtube/v3/videos"
UP = "https://www.googleapis.com/upload/youtube/v3/videos"


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "youtube_client_id", "cid")
    monkeypatch.setattr(settings, "youtube_client_secret", "csecret")
    monkeypatch.setattr(youtube, "TOKEN_FILE", tmp_path / "yt.json")
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


def connect_now():
    youtube.TOKEN_FILE.write_text(json.dumps({"refresh_token": "RT"}))


def mock_upload(vid="VID1"):
    respx.post(TOK).mock(return_value=httpx.Response(200, json={"access_token": "AT"}))
    init = respx.post(UP).mock(return_value=httpx.Response(200, headers={"location": "https://up.test/session"}))
    respx.put("https://up.test/session").mock(return_value=httpx.Response(200, json={"id": vid}))
    return init


def video():
    return {"file": ("clip.mp4", io.BytesIO(b"x" * 2048), "video/mp4")}


async def test_status_before_connecting(client):
    d = (await client.get("/api/youtube/status")).json()
    assert d["configured"] is True and d["connected"] is False and d["channel"] is None


async def test_connect_url_and_callback_saves_token(client):
    url = (await client.get("/api/youtube/connect")).json()["url"]
    q = parse_qs(urlparse(url).query)
    assert q["client_id"] == ["cid"] and q["access_type"] == ["offline"] and "youtube.upload" in q["scope"][0]
    with respx.mock:
        respx.post(TOK).mock(return_value=httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT"}))
        r = await client.get("/api/youtube/callback", params={"code": "abc", "state": q["state"][0]})
    assert r.status_code == 307 and r.headers["location"].endswith("#/youtube?connected=1")
    assert youtube.connected()
    bad = await client.get("/api/youtube/callback", params={"code": "abc", "state": "forged"})
    assert "error=" in bad.headers["location"]


@respx.mock
async def test_publish_now_uploads_public_then_becomes_published(client):
    connect_now()
    init = mock_upload()
    r = await client.post("/api/youtube/posts", files=video(), data={"title": "My title", "description": "D", "tags": "a, #b", "privacy": "public", "mode": "now"})
    assert r.status_code == 200, r.text
    meta = json.loads(init.calls[0].request.content)
    assert meta["status"] == {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    assert meta["snippet"]["title"] == "My title" and meta["snippet"]["tags"] == ["a", "b"]
    assert r.json()["items"][0]["status"] == "PUBLISHING"
    respx.get(VID).mock(return_value=httpx.Response(200, json={"items": [{"status": {"uploadStatus": "processed", "privacyStatus": "public"}}]}))
    h = (await client.get("/api/youtube/posts")).json()["items"][0]
    assert h["status"] == "PUBLISHED" and h["post_url"].endswith("VID1") and h["error"] is None


@respx.mock
async def test_schedule_uploads_private_with_publish_at(client):
    connect_now()
    init = mock_upload("VID2")
    soon = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(minutes=3)).strftime("%Y-%m-%dT%H:%M")
    r = await client.post("/api/youtube/posts", files=video(), data={"title": "T", "mode": "schedule", "scheduled_at": soon, "tz": "Asia/Dubai"})
    assert r.status_code == 422
    later = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    r = await client.post("/api/youtube/posts", files=video(), data={"title": "T", "mode": "schedule", "scheduled_at": later, "tz": "Asia/Dubai"})
    assert r.status_code == 200, r.text
    st = json.loads(init.calls[0].request.content)["status"]
    assert st["privacyStatus"] == "private" and st["publishAt"].endswith("Z")
    respx.get(VID).mock(return_value=httpx.Response(200, json={"items": [{"status": {"uploadStatus": "processed", "privacyStatus": "private", "publishAt": st["publishAt"]}}]}))
    assert (await client.get("/api/youtube/posts")).json()["items"][0]["status"] == "SCHEDULED"
    respx.get(VID).mock(return_value=httpx.Response(200, json={"items": [{"status": {"uploadStatus": "processed", "privacyStatus": "public"}}]}))
    assert (await client.get("/api/youtube/posts")).json()["items"][0]["status"] == "PUBLISHED"


@respx.mock
async def test_unverified_project_kept_private_is_explained(client):
    connect_now()
    mock_upload("VID3")
    await client.post("/api/youtube/posts", files=video(), data={"title": "T", "privacy": "public"})
    respx.get(VID).mock(return_value=httpx.Response(200, json={"items": [{"status": {"uploadStatus": "processed", "privacyStatus": "private"}}]}))
    h = (await client.get("/api/youtube/posts")).json()["items"][0]
    assert h["status"] == "PUBLISHED" and "kept this video private" in h["error"]


async def test_publish_needs_connection_and_title(client):
    r = await client.post("/api/youtube/posts", files=video(), data={"title": "T"})
    assert r.status_code == 401 and "not connected" in r.json()["detail"]
    r = await client.post("/api/youtube/posts", files=video(), data={"title": "  "})
    assert r.status_code == 422
