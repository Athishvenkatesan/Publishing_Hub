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
import yt_accounts
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
    monkeypatch.setattr(yt_accounts, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(yt_accounts, "ENV_FILE", tmp_path / "none.env")  # never read the real .env in tests
    monkeypatch.setattr(yt_accounts, "ACCOUNTS_FILE", tmp_path / "accounts.json")  # nor the real accounts file
    monkeypatch.delenv("YOUTUBE_ACCOUNTS", raising=False)
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


def connect_now(key="main", token="RT"):
    p = yt_accounts.token_path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"refresh_token": token}))


def mock_upload(vid="VID1"):
    respx.post(TOK).mock(return_value=httpx.Response(200, json={"access_token": "AT"}))
    init = respx.post(UP).mock(return_value=httpx.Response(200, headers={"location": "https://up.test/session"}))
    respx.put("https://up.test/session").mock(return_value=httpx.Response(200, json={"id": vid}))
    return init


def video():
    return {"file": ("clip.mp4", io.BytesIO(b"x" * 2048), "video/mp4")}


@respx.mock
async def test_status_before_connecting(client):
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="<html>Sign in - Choose an account</html>"))
    d = (await client.get("/api/youtube/status")).json()
    assert d["configured"] is True and d["connected"] is False and d["channel"] is None and d["setup_problem"] == ""


@respx.mock
async def test_status_explains_redirect_mismatch_before_the_user_hits_googles_error(client):
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="Error 400: redirect_uri_mismatch"))
    d = (await client.get("/api/youtube/status")).json()
    assert "Authorized redirect URIs" in d["setup_problem"] and "/api/youtube/callback" in d["setup_problem"]


async def test_connect_url_and_callback_saves_token(client):
    url = (await client.get("/api/youtube/connect")).json()["url"]
    q = parse_qs(urlparse(url).query)
    assert q["client_id"] == ["cid"] and q["access_type"] == ["offline"] and "youtube.upload" in q["scope"][0]
    with respx.mock:
        respx.post(TOK).mock(return_value=httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT"}))
        r = await client.get("/api/youtube/callback", params={"code": "abc", "state": q["state"][0]})
    assert r.status_code == 307 and r.headers["location"].endswith("#/youtube?connected=1&account=main")
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
    assert meta["status"] == {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "license": "youtube", "embeddable": True,
                              "publicStatsViewable": True, "containsSyntheticMedia": False}
    assert meta["snippet"]["categoryId"] == "22" and init.calls[0].request.url.params["notifySubscribers"] == "true"
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


@respx.mock
async def test_advanced_options_reach_youtube(client):
    connect_now()
    init = mock_upload("VID4")
    r = await client.post("/api/youtube/posts", files=video(), data={
        "title": "T", "category_id": "27", "made_for_kids": "true", "language": "ar", "license": "creativeCommon",
        "embeddable": "false", "public_stats": "false", "synthetic": "true", "notify": "false"})
    assert r.status_code == 200, r.text
    meta = json.loads(init.calls[0].request.content)
    assert meta["snippet"]["categoryId"] == "27" and meta["snippet"]["defaultLanguage"] == "ar"
    assert meta["status"] | {} == {**meta["status"], "selfDeclaredMadeForKids": True, "license": "creativeCommon", "embeddable": False,
                                   "publicStatsViewable": False, "containsSyntheticMedia": True}
    assert init.calls[0].request.url.params["notifySubscribers"] == "false"
    bad = await client.post("/api/youtube/posts", files=video(), data={"title": "T", "category_id": "999"})
    assert bad.status_code == 422


def processing(status):
    return httpx.Response(200, json={"items": [{"status": {"uploadStatus": "processed"}, "processingDetails": {"processingStatus": status}}]})


@respx.mock
async def test_thumbnail_waits_for_processing_then_is_set(client, tmp_path, monkeypatch):
    import yt_thumbnail
    monkeypatch.setattr(yt_thumbnail, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(yt_thumbnail, "POLL_S", 0.01)
    connect_now()
    mock_upload("VID5")
    started = []
    monkeypatch.setattr(yt_thumbnail, "start", lambda a, v: started.append(v))  # run apply() ourselves, deterministically
    files = {**video(), "thumbnail": ("t.png", io.BytesIO(b"p" * 100), "image/png")}
    r = await client.post("/api/youtube/posts", files=files, data={"title": "T"})
    assert r.status_code == 200 and r.json()["thumbnail"] == "pending" and started == ["VID5"]
    assert (tmp_path / "pending" / "main~VID5.png").exists()
    ok = respx.post(youtube.THUMB).mock(return_value=httpx.Response(200, json={}))
    respx.get(VID).mock(side_effect=[processing("processing"), processing("succeeded")])  # a Short is not ready on the first look
    await yt_thumbnail.apply("main", "VID5")
    assert ok.call_count == 1 and ok.calls[0].request.url.params["videoId"] == "VID5"
    assert not (tmp_path / "pending" / "main~VID5.png").exists()


@respx.mock
async def test_thumbnail_failure_is_a_note_not_a_failed_upload(client, tmp_path, monkeypatch):
    import yt_thumbnail
    monkeypatch.setattr(yt_thumbnail, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(yt_thumbnail, "start", lambda a, v: None)
    connect_now()
    mock_upload("VID6")
    files = {**video(), "thumbnail": ("t.png", io.BytesIO(b"p" * 100), "image/png")}
    await client.post("/api/youtube/posts", files=files, data={"title": "T"})
    respx.get(VID).mock(return_value=processing("succeeded"))
    respx.post(youtube.THUMB).mock(return_value=httpx.Response(403, json={"error": {"message": "channel not verified"}}))
    await yt_thumbnail.apply("main", "VID6")
    h = (await client.get("/api/youtube/posts")).json()["items"][0]
    assert h["error"].startswith("Thumbnail not set: ") and "channel not verified" in h["error"]
    assert h["status"] in ("PUBLISHING", "PUBLISHED")  # the upload itself is fine


async def test_bad_thumbnail_is_skipped_with_a_warning(client):
    connect_now()
    with respx.mock:
        mock_upload("VID7")
        files = {**video(), "thumbnail": ("t.gif", io.BytesIO(b"p"), "image/gif")}
        r = await client.post("/api/youtube/posts", files=files, data={"title": "T"})
    assert r.status_code == 200 and r.json()["thumbnail"] == "none" and "Thumbnail skipped" in r.json()["warnings"][0]


@respx.mock
async def test_unverified_channel_thumbnail_refusal_is_explained(client, tmp_path, monkeypatch):
    import yt_thumbnail
    monkeypatch.setattr(yt_thumbnail, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(yt_thumbnail, "start", lambda a, v: None)
    connect_now()
    mock_upload("VID8")
    files = {**video(), "thumbnail": ("t.png", io.BytesIO(b"p" * 100), "image/png")}
    await client.post("/api/youtube/posts", files=files, data={"title": "T"})
    respx.get(VID).mock(return_value=processing("succeeded"))
    respx.post(youtube.THUMB).mock(return_value=httpx.Response(403, json={"error": {
        "message": "The authenticated user doesn't have permissions to upload and set custom video thumbnails.", "errors": [{"reason": "forbidden"}]}}))
    await yt_thumbnail.apply("main", "VID8")
    err = (await client.get("/api/youtube/posts")).json()["items"][0]["error"]
    assert "youtube.com/verify" in err and "The video itself is fine" in err


@respx.mock
async def test_status_tells_the_screen_whether_the_channel_is_verified(client):
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="Sign in"))
    connect_now()
    respx.post(TOK).mock(return_value=httpx.Response(200, json={"access_token": "AT"}))
    for flag, expect in (("eligible", False), ("allowed", True)):
        respx.get("https://www.googleapis.com/youtube/v3/channels").mock(return_value=httpx.Response(200, json={"items": [
            {"id": "UC1", "snippet": {"title": "C"}, "statistics": {}, "status": {"longUploadsStatus": flag}}]}))
        ch = (await client.get("/api/youtube/status")).json()["channel"]
        assert ch["verified"] is expect and ch["verify_url"] == "https://www.youtube.com/verify"


@respx.mock
async def test_connect_with_check_refuses_instead_of_sending_the_user_to_googles_error_page(client):
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="Error 400: redirect_uri_mismatch"))
    r = await client.get("/api/youtube/connect", params={"check": True})
    assert r.status_code == 409 and "Authorized redirect URIs" in r.json()["detail"] and "Desktop app" in r.json()["detail"]
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="Sign in"))
    ok = await client.get("/api/youtube/connect", params={"check": True})
    assert ok.status_code == 200 and ok.json()["url"].startswith("https://accounts.google.com")


def auth_by_address(ok_for: list[str]):
    """Google's sign-in page: fine for the listed redirect addresses, redirect_uri_mismatch for any other."""
    def handler(request):
        uri = request.url.params["redirect_uri"]
        return httpx.Response(200, text="Sign in" if uri in ok_for else "Error 400: redirect_uri_mismatch")
    respx.get(youtube.AUTH).mock(side_effect=handler)


@respx.mock
async def test_a_client_that_only_lists_the_web_page_address_still_signs_in(client):
    """The slip we saw: the client lists http://localhost:3100 (the page) but not the backend address."""
    auth_by_address([settings.frontend_url])
    r = await client.get("/api/youtube/connect", params={"check": True})
    assert r.status_code == 200 and r.json()["redirect_uri"] == settings.frontend_url
    q = parse_qs(urlparse(r.json()["url"]).query)
    assert q["redirect_uri"] == [settings.frontend_url]
    sent = {}

    def token(request):
        sent.update(dict(x.split("=", 1) for x in request.content.decode().split("&")))
        return httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT"})
    respx.post(TOK).mock(side_effect=token)
    back = await client.get("/api/youtube/callback", params={"code": "abc", "state": q["state"][0]})
    assert back.headers["location"].endswith("connected=1&account=main") and youtube.connected()
    from urllib.parse import unquote
    assert unquote(sent["redirect_uri"]) == settings.frontend_url  # the exchange uses the same address as the link


@respx.mock
async def test_the_backend_address_is_preferred_when_both_work(client):
    auth_by_address([settings.youtube_redirect_uri, settings.frontend_url])
    assert (await client.get("/api/youtube/connect", params={"check": True})).json()["redirect_uri"] == settings.youtube_redirect_uri


@respx.mock
async def test_when_neither_address_is_listed_the_message_names_both(client):
    auth_by_address([])
    r = await client.get("/api/youtube/connect", params={"check": True})
    d = r.json()["detail"]
    assert r.status_code == 409 and settings.youtube_redirect_uri in d and settings.frontend_url in d and "not under JavaScript origins" in d
    status = (await client.get("/api/youtube/status")).json()
    assert status["setup_problem"] == d
