"""Meta accounts manager: read the two tokens, replace them (swapped for 60-day ones when the app secret is known), expiry dates."""
import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

import envfile
import meta
from config import settings

G = "https://graph.facebook.com"
V = f"{G}/v21.0"
TH = "https://graph.threads.net"
SHORT = "EAAshort" + "x" * 30


@pytest.fixture
async def client(monkeypatch):
    envfile.ENV.write_text("META_ACCESS_TOKEN=\nTHREADS_ACCESS_TOKEN=\n")
    monkeypatch.setattr(meta, "ENV", envfile.ENV)
    monkeypatch.setattr(meta, "_seen", {"mtime": 0.0})
    monkeypatch.setattr(settings, "meta_access_token", "")
    monkeypatch.setattr(settings, "threads_access_token", "")
    import app as appmod
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        yield c


def meta_ok(token, expires_at=1900000000):
    respx.get(f"{G}/debug_token").mock(return_value=httpx.Response(200, json={"data": {"is_valid": True, "expires_at": expires_at, "app_id": 555, "scopes": ["pages_manage_posts"]}}))
    respx.get(f"{V}/me").mock(return_value=httpx.Response(200, json={"id": "1", "name": "Dgm"}))
    respx.get(f"{V}/me/permissions").mock(return_value=httpx.Response(200, json={"data": [{"permission": "pages_manage_posts", "status": "granted"}]}))
    respx.get(f"{V}/me/accounts").mock(return_value=httpx.Response(200, json={"data": [{"id": "P1", "name": "Page ", "tasks": ["CREATE_CONTENT"], "instagram_business_account": {"id": "IG", "username": "dgm"}}]}))


async def test_empty_tokens_show_as_missing(client):
    d = (await client.get("/api/meta/manager/accounts")).json()
    assert [(a["key"], a["has_token"]) for a in d["accounts"]] == [("meta", False), ("threads", False)] and d["guide"]


@respx.mock
async def test_paste_a_token_without_secret_keeps_it_and_learns_the_app_id(client):
    meta_ok(SHORT)
    d = (await client.patch("/api/meta/manager/accounts/meta", json={"token": SHORT, "expires_on": "2027-02-01"})).json()
    assert d["valid"] and d["who"] == "Dgm" and d["expires_at"] == 1900000000 and d["expires_on"] == "2027-02-01" and d["pages"] == [{"name": "Page", "instagram": "dgm"}]
    assert d["token_hint"] == SHORT[:8] + "..." and SHORT not in str(d)
    v = envfile.read()
    assert v["META_ACCESS_TOKEN"] == SHORT and v["META_APP_ID"] == "555" and settings.meta_access_token == SHORT


@respx.mock
async def test_with_the_app_secret_a_token_becomes_a_60_day_one(client):
    meta_ok(SHORT)
    swap = respx.get(f"{V}/oauth/access_token").mock(return_value=httpx.Response(200, json={"access_token": "EAAlong" + "y" * 30, "expires_in": 5184000}))
    await client.patch("/api/meta/manager/accounts/meta", json={"app_id": "555", "app_secret": "sec"})
    await client.patch("/api/meta/manager/accounts/meta", json={"token": SHORT})
    q = swap.calls[0].request.url.params
    assert q["grant_type"] == "fb_exchange_token" and q["client_secret"] == "sec" and q["fb_exchange_token"] == SHORT
    assert envfile.read()["META_ACCESS_TOKEN"].startswith("EAAlong")
    assert (await client.post("/api/meta/manager/accounts/meta/extend")).status_code == 200


@respx.mock
async def test_threads_token_is_extended_and_its_expiry_saved(client):
    respx.get(f"{TH}/access_token").mock(return_value=httpx.Response(200, json={"access_token": "THlong" + "z" * 30, "expires_in": 86400}))
    respx.get(f"{TH}/v1.0/me").mock(return_value=httpx.Response(200, json={"id": "9", "username": "dgm"}))
    await client.patch("/api/meta/manager/accounts/threads", json={"app_secret": "thsec"})
    d = (await client.patch("/api/meta/manager/accounts/threads", json={"token": "THshort" + "z" * 30})).json()
    assert d["valid"] and d["who"] == "@dgm" and d["expires_at"] and envfile.read()["THREADS_ACCESS_TOKEN"].startswith("THlong")


async def test_bad_input_is_refused(client):
    assert (await client.patch("/api/meta/manager/accounts/meta", json={"token": "short"})).status_code == 422
    assert (await client.patch("/api/meta/manager/accounts/meta", json={"app_id": "abc"})).status_code == 422
    assert (await client.patch("/api/meta/manager/accounts/meta", json={"expires_on": "tomorrow"})).status_code == 422
    assert (await client.post("/api/meta/manager/accounts/meta/extend")).status_code == 422
    assert (await client.get("/api/meta/manager/accounts/nope/check")).status_code == 404


async def test_edit_values_show_the_saved_token_and_secret(client):
    envfile.set_values({"META_ACCESS_TOKEN": SHORT, "META_APP_ID": "555", "META_APP_SECRET": "sec", "THREADS_APP_SECRET": "ts"})
    assert (await client.get("/api/meta/manager/accounts/meta/values")).json() == {"token": SHORT, "app_id": "555", "app_secret": "sec", "expires_on": ""}
    assert (await client.get("/api/meta/manager/accounts/threads/values")).json()["app_secret"] == "ts"
    assert (await client.get("/api/meta/manager/accounts/nope/values")).status_code == 404
