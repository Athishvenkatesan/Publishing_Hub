import json
import stat
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

import yt_accounts
import yt_studio
import youtube
from .test_youtube import TOK, client, connect_now  # noqa: F401  (shared fixtures)

ENV = "YOUTUBE_ACCOUNTS=main1\nYOUTUBE_MAIN1_LABEL=main@example.com\nYOUTUBE_MAIN1_CLIENT_ID=111-abc.apps.googleusercontent.com\nYOUTUBE_MAIN1_CLIENT_SECRET=env-secret-value\n"
GOOD_ID = "222-def.apps.googleusercontent.com"
G = "https://www.googleapis.com/youtube/v3"
INFO = "https://oauth2.googleapis.com/tokeninfo"
AN = "https://youtubeanalytics.googleapis.com/v2/reports"
SC = "https://www.googleapis.com/auth/"


@pytest.fixture(autouse=True)
def stores(client, tmp_path, monkeypatch):  # runs after `client`, which resets the .env path
    env = tmp_path / "m.env"
    env.write_text(ENV)
    monkeypatch.setattr(yt_accounts, "ENV_FILE", env)
    monkeypatch.setattr(yt_accounts, "ACCOUNTS_FILE", tmp_path / "accounts.json")
    yt_studio._cache.clear()
    yt_studio._uploads.clear()


async def add(client, **kw):
    return await client.post("/api/youtube/manager/accounts", json={"label": "athish0204@gmail.com", "client_id": GOOD_ID, "client_secret": "secret-value-1", **kw})


async def test_list_never_exposes_a_secret_and_marks_env_accounts_read_only(client):
    r = await client.get("/api/youtube/manager/accounts")
    d = r.json()
    a = d["accounts"][0]
    assert a["key"] == "main1" and a["source"] == "env" and a["client_hint"] == "111-abc.apps..." and a["has_secret"] is True
    assert "env-secret-value" not in r.text and "client_secret" not in a and d["redirect_uri"].endswith("/api/youtube/callback")
    assert len(d["guide"]) == 6 and d["guide"][0]["link"]["url"].startswith("https://console.cloud.google.com")


async def test_add_validates_stores_privately_and_hides_the_secret(client):
    for bad in ({"client_id": "nope"}, {"client_secret": "short"}, {"label": "  "}):
        r = await add(client, **bad)
        assert r.status_code == 422, bad
    r = await add(client)
    assert r.status_code == 201, r.text
    card = r.json()
    assert card["key"] == "athish0204" and card["source"] == "file" and card["configured"] and "secret-value-1" not in r.text
    assert stat.S_IMODE(yt_accounts.ACCOUNTS_FILE.stat().st_mode) == 0o600  # holds a secret
    assert (await add(client)).json()["key"] == "athish02042"  # same label again gets its own key
    listed = (await client.get("/api/youtube/accounts")).json()["accounts"]
    assert [a["key"] for a in listed] == ["main1", "athish0204", "athish02042"]


async def test_another_channel_can_reuse_an_existing_google_app(client):
    r = await add(client, label="Second channel", client_id="", client_secret="", client_from="main1")
    assert r.status_code == 201 and r.json()["client_from"] == "main1" and r.json()["configured"]
    url = (await client.get("/api/youtube/connect", params={"account": r.json()["key"]})).json()["url"]
    assert parse_qs(urlparse(url).query)["client_id"] == ["111-abc.apps.googleusercontent.com"]  # signs in with main1's client
    assert (await add(client, label="X", client_id="", client_secret="", client_from="ghost")).status_code == 422
    assert (await client.delete("/api/youtube/manager/accounts/main1")).status_code == 409  # env accounts are edited in .env


async def test_rename_remove_and_the_rules_for_env_accounts(client):
    key = (await add(client)).json()["key"]
    r = await client.patch(f"/api/youtube/manager/accounts/{key}", json={"label": "Renamed"})
    assert r.status_code == 200 and r.json()["label"] == "Renamed" and r.json()["key"] == key
    assert (await client.patch("/api/youtube/manager/accounts/main1", json={"label": "x"})).status_code == 409
    assert (await client.patch(f"/api/youtube/manager/accounts/{key}", json={"client_id": "bad"})).status_code == 422
    connect_now(key)
    assert yt_accounts.token_path(key).exists()
    assert (await client.delete(f"/api/youtube/manager/accounts/{key}")).json() == {"ok": True}
    assert not yt_accounts.token_path(key).exists() and (await client.get("/api/youtube/manager/accounts/nope/check")).status_code == 404
    parent = (await add(client)).json()["key"]
    await add(client, label="Child", client_id="", client_secret="", client_from=parent)
    assert (await client.delete(f"/api/youtube/manager/accounts/{parent}")).status_code == 409  # a channel still uses its Google app


def statuses(d):
    return {i["id"]: i["status"] for i in d["items"]}


@respx.mock
async def test_checklist_walks_from_setup_to_sign_in(client):
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="Error 400: redirect_uri_mismatch"))
    d = (await client.get("/api/youtube/manager/accounts/main1/check")).json()
    assert statuses(d) == {"client": "ok", "redirect": "todo", "signin": "todo"}
    assert next(i for i in d["items"] if i["id"] == "redirect")["action"]["kind"] == "copy"
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="Sign in"))
    assert statuses((await client.get("/api/youtube/manager/accounts/main1/check")).json())["redirect"] == "ok"
    unfinished = await client.post("/api/youtube/manager/accounts", json={"label": "A", "client_id": GOOD_ID, "client_secret": "secret-value-1"})
    yt_accounts.use(unfinished.json()["key"])
    half = await client.patch(f"/api/youtube/manager/accounts/{unfinished.json()['key']}", json={"label": "B"})
    assert half.json()["configured"] is True


@respx.mock
async def test_checklist_for_a_signed_in_account_reports_verification_and_permissions(client):
    connect_now("main1")
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="Sign in"))
    respx.post(TOK).mock(return_value=httpx.Response(200, json={"access_token": "AT"}))
    respx.get(INFO).mock(return_value=httpx.Response(200, json={"scope": f"{SC}youtube.upload {SC}youtube.readonly"}))
    respx.get(f"{G}/channels").mock(return_value=httpx.Response(200, json={"items": [
        {"id": "UC1", "snippet": {"title": "C", "customUrl": "@c"}, "statistics": {}, "status": {"longUploadsStatus": "eligible"}}]}))
    d = (await client.get("/api/youtube/manager/accounts/main1/check")).json()
    assert statuses(d) == {"client": "ok", "redirect": "ok", "signin": "ok", "channel": "ok", "verified": "todo", "manage": "todo", "reports": "todo"}
    assert next(i for i in d["items"] if i["id"] == "verified")["action"]["url"] == "https://www.youtube.com/verify"
    assert next(i for i in d["items"] if i["id"] == "manage")["action"]["opts"] == {"manage": True}
    # reports permission granted, but the Analytics API is off in the Google project
    respx.get(INFO).mock(return_value=httpx.Response(200, json={"scope": f"{SC}youtube.upload {SC}youtube.readonly {SC}yt-analytics.readonly {SC}youtube"}))
    respx.get(AN).mock(return_value=httpx.Response(403, json={"error": {"message": "YouTube Analytics API has not been used in project 1 before or it is disabled.", "errors": [{"reason": "accessNotConfigured"}]}}))
    d = (await client.get("/api/youtube/manager/accounts/main1/check")).json()
    rep = next(i for i in d["items"] if i["id"] == "reports")
    assert rep["status"] == "todo" and rep["action"]["url"].endswith("youtubeanalytics.googleapis.com") and statuses(d)["manage"] == "ok"


@respx.mock
async def test_the_fix_hint_matches_how_the_account_was_added(client):
    key = (await add(client)).json()["key"]
    respx.get(youtube.AUTH).mock(return_value=httpx.Response(200, text="Error 401: invalid_client"))
    onscreen = next(i for i in (await client.get(f"/api/youtube/manager/accounts/{key}/check")).json()["items"] if i["id"] == "redirect")
    assert "Remove this account and add it again" in onscreen["detail"] and ".env" not in onscreen["detail"]
    fromenv = next(i for i in (await client.get("/api/youtube/manager/accounts/main1/check")).json()["items"] if i["id"] == "redirect")
    assert "YOUTUBE_MAIN1_CLIENT_ID" in fromenv["detail"] and "backend/.env" in fromenv["detail"]


async def test_a_handle_label_gets_a_sensible_key(client):
    r = await add(client, label="@GenVideoAIforKids")
    assert r.json()["key"] == "genvideoaiforkids"
    assert (await add(client, label="@@")).json()["key"] == "account"
