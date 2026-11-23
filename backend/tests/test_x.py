import base64
import hashlib
import io
import json
import stat
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

import x_accounts
import xapi
from .test_youtube import client  # noqa: F401  (shared database + app fixture)

API = xapi.API
CID, SECRET = "VE9aZ0ZVZmhrY2xYc0hPNkVQRE46MTpjaQ", "x-secret-value-123456"


@pytest.fixture(autouse=True)
def stores(client, tmp_path, monkeypatch):  # never touch the real accounts file or sign-ins
    monkeypatch.setattr(x_accounts, "ACCOUNTS_FILE", tmp_path / "x_accounts.json")
    monkeypatch.setattr(x_accounts, "TOKENS_DIR", tmp_path / "x_tokens")

    async def instant(_):
        return None
    monkeypatch.setattr(xapi.asyncio, "sleep", instant)


def add(label="a@example.com", cid=CID, secret=SECRET):
    return x_accounts.add(label, cid, secret)


def sign_in(key, uid="U1", scope="tweet.read tweet.write users.read media.write offline.access", expires_in=3600, refresh="RT"):
    p = x_accounts.token_path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"access_token": f"AT-{key}", "refresh_token": refresh, "expires_at": int(time.time()) + expires_in, "scope": scope,
                             "id": uid, "name": f"Name {key}", "username": f"user_{key}"}))


def clip(name="clip.mp4", size=2048):
    return {"file": (name, io.BytesIO(b"x" * size), "video/mp4")}


def mock_upload(mid="M1", post="P1", processing=True):
    init = respx.post(f"{API}/media/upload/initialize").mock(return_value=httpx.Response(200, json={"data": {"id": mid}}))
    app = respx.post(f"{API}/media/upload/{mid}/append").mock(return_value=httpx.Response(204))
    fin = respx.post(f"{API}/media/upload/{mid}/finalize").mock(return_value=httpx.Response(200, json={"data": {"id": mid, "processing_info": {"state": "pending", "check_after_secs": 1} if processing else None}}))
    st = respx.get(f"{API}/media/upload").mock(return_value=httpx.Response(200, json={"data": {"processing_info": {"state": "succeeded"}}}))
    tw = respx.post(f"{API}/tweets").mock(return_value=httpx.Response(201, json={"data": {"id": post, "text": "t"}}))
    return init, app, fin, st, tw


# ---------- accounts and sign-in ----------
def test_account_store_is_its_own_and_validates():
    a = add("Gov Media@x.com")
    assert a.key == "govmedia" and stat.S_IMODE(x_accounts.ACCOUNTS_FILE.stat().st_mode) == 0o600
    with pytest.raises(ValueError):
        x_accounts.add("b", "bad id!", SECRET)
    assert x_accounts.add("Second", client_from="govmedia").client_id == CID


async def test_connect_uses_pkce_and_the_127_callback_then_saves_the_sign_in(client):
    add()
    url = (await client.get("/api/x/connect", params={"back": "popup"})).json()["url"]
    q = parse_qs(urlparse(url).query)
    assert url.startswith(xapi.AUTH) and q["redirect_uri"] == ["http://127.0.0.1:8100/api/x/callback"] and q["code_challenge_method"] == ["S256"]
    assert set(q["scope"][0].split()) == {"tweet.read", "tweet.write", "users.read", "media.write", "offline.access"} and q["client_id"] == [CID]
    with respx.mock:
        tok = respx.post(xapi.TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT", "expires_in": 7200, "scope": xapi.SCOPES}))
        respx.get(f"{API}/users/me").mock(return_value=httpx.Response(200, json={"data": {"id": "42", "name": "Gov", "username": "govmedia"}}))
        r = await client.get("/api/x/callback", params={"code": "c", "state": q["state"][0]})
    assert r.headers["location"].endswith("#/x/done?connected=1&account=a")
    req = tok.calls[0].request
    form = parse_qs(req.content.decode())
    assert req.headers["authorization"] == "Basic " + base64.b64encode(f"{CID}:{SECRET}".encode()).decode()
    verifier = form["code_verifier"][0]
    assert base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode() == q["code_challenge"][0]
    x_accounts.use("a")
    assert xapi.connected() and xapi.saved()["username"] == "govmedia" and stat.S_IMODE(x_accounts.token_path("a").stat().st_mode) == 0o600
    bad = await client.get("/api/x/callback", params={"error": "access_denied", "state": "forged"})
    assert "error=You%20did%20not%20allow" in bad.headers["location"]


@respx.mock
async def test_an_old_access_token_is_renewed_and_the_new_refresh_token_kept(client):
    add(); sign_in("a", expires_in=-10, refresh="RT-old")
    ref = respx.post(xapi.TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "AT-new", "refresh_token": "RT-new", "expires_in": 7200}))
    respx.get(f"{API}/users/me").mock(return_value=httpx.Response(200, json={"data": {"id": "U1", "name": "N", "username": "u"}}))
    items = {i["id"]: i for i in (await client.get("/api/x/manager/accounts/a/check")).json()["items"]}
    assert items["signin"]["status"] == "ok" and parse_qs(ref.calls[0].request.content.decode())["refresh_token"] == ["RT-old"]
    x_accounts.use("a")
    assert xapi.saved()["access_token"] == "AT-new" and xapi.saved()["refresh_token"] == "RT-new"
    respx.post(xapi.TOKEN).mock(return_value=httpx.Response(400, json={"error": "invalid_request"}))
    sign_in("a", expires_in=-10)
    items = {i["id"]: i for i in (await client.get("/api/x/manager/accounts/a/check")).json()["items"]}
    assert items["signin"]["status"] == "warn" and "sign in again" in items["signin"]["detail"]


# ---------- posting ----------
@respx.mock
async def test_post_to_two_accounts_uploads_in_parts_then_posts(client, monkeypatch):
    monkeypatch.setattr(xapi, "SEGMENT", 1000)  # 2048 bytes -> 3 parts
    add("a@example.com"); add("b@example.com"); sign_in("a", "UA"); sign_in("b", "UB")
    init, app, fin, st, tw = mock_upload()
    r = await client.post("/api/x/posts/multi", files=clip(), data={"text": "Save water #Dubai", "reply": "following", "accounts": ["a", "b"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["items"]) == 2 and d["errors"] == [] and d["items"][0]["group_id"] == d["items"][1]["group_id"]
    assert json.loads(init.calls[0].request.content) == {"media_type": "video/mp4", "total_bytes": 2048, "media_category": "tweet_video"}
    assert app.call_count == 6 and b'name="segment_index"\r\n\r\n2' in app.calls[2].request.content
    assert st.called and json.loads(tw.calls[0].request.content) == {"text": "Save water #Dubai", "media": {"media_ids": ["M1"]}, "reply_settings": "following"}
    assert tw.calls[0].request.headers["authorization"] in ("Bearer AT-a", "Bearer AT-b")
    h = (await client.get("/api/x/posts")).json()["items"]
    assert len(h) == 2 and h[0]["platform"] == "x" and h[0]["post_url"].startswith("https://x.com/user_") and h[0]["post_url"].endswith("/status/P1")
    assert (await client.get("/api/posts")).json()["items"] == []  # the Zernio screen never lists these


@respx.mock
async def test_no_credits_on_one_account_does_not_stop_the_other(client):
    add("a@example.com"); add("b@example.com"); sign_in("a"); sign_in("b")
    mock_upload(processing=False)
    respx.post(f"{API}/media/upload/initialize").mock(side_effect=[
        httpx.Response(402, json={"title": "CreditsDepleted", "detail": "Your enrolled account does not have any credits"}),
        httpx.Response(200, json={"data": {"id": "M1"}})])
    d = (await client.post("/api/x/posts/multi", files=clip(), data={"text": "Hi", "accounts": ["a", "b"]})).json()
    assert len(d["items"]) == 1 and len(d["errors"]) == 1 and "credits" in d["errors"][0]["error"]


@pytest.mark.parametrize("data,name,msg", [
    ({"text": " ", "accounts": ["a"]}, "clip.mp4", "post text"),
    ({"text": "x" * 25001, "accounts": ["a"]}, "clip.mp4", "post text"),
    ({"text": "Hi", "reply": "nobody", "accounts": ["a"]}, "clip.mp4", "Who can reply"),
    ({"text": "Hi", "accounts": ["a"]}, "clip.avi", "MP4 or MOV"),
    ({"text": "Hi", "accounts": ["zz"]}, "clip.mp4", "Unknown X account"),
])
async def test_bad_requests_are_refused_before_anything_is_sent(client, data, name, msg):
    add(); sign_in("a")
    r = await client.post("/api/x/posts/multi", files=clip(name, 100), data=data)
    assert r.status_code == 422 and msg in r.json()["detail"]


@respx.mock
async def test_delete_and_remove_from_list(client):
    add(); sign_in("a")
    mock_upload(processing=False)
    await client.post("/api/x/posts/multi", files=clip(), data={"text": "One", "accounts": ["a"]})
    row = (await client.get("/api/x/posts")).json()["items"][0]
    assert (await client.get(f"/api/x/posts/{row['id']}/details")).json()["text"] == "One"
    gone = respx.delete(f"{API}/tweets/P1").mock(return_value=httpx.Response(200, json={"data": {"deleted": True}}))
    assert (await client.delete(f"/api/x/posts/{row['id']}")).status_code == 200 and gone.called
    await client.post("/api/x/posts/multi", files=clip(), data={"text": "Two", "accounts": ["a"]})
    row = (await client.get("/api/x/posts")).json()["items"][0]
    keep = respx.delete(url__regex=r".*/tweets/.*").mock(return_value=httpx.Response(200))
    assert (await client.delete(f"/api/x/posts/{row['id']}/local")).status_code == 200 and not keep.called


# ---------- manager ----------
@respx.mock
async def test_manager_hides_secrets_and_the_checklist_walks_to_ready(client):
    r = await client.post("/api/x/manager/accounts", json={"label": "a@example.com", "client_id": CID, "client_secret": SECRET})
    assert r.status_code == 201 and SECRET not in r.text
    d = (await client.get("/api/x/manager/accounts")).json()
    assert d["redirect_uri"] == "http://127.0.0.1:8100/api/x/callback" and len(d["guide"]) == 6 and "127.0.0.1" in d["guide"][2]["do"]
    items = {i["id"]: i for i in (await client.get("/api/x/manager/accounts/a/check")).json()["items"]}
    assert items["callback"]["status"] == "todo" and [a["kind"] for a in items["callback"]["action"]] == ["copy", "link"] and items["signin"]["action"]["kind"] == "connect"
    sign_in("a", scope="tweet.read users.read offline.access")
    respx.get(f"{API}/users/me").mock(return_value=httpx.Response(200, json={"data": {"id": "U1", "name": "Gov", "username": "gov"}}))
    items = {i["id"]: i for i in (await client.get("/api/x/manager/accounts/a/check")).json()["items"]}
    assert items["callback"]["status"] == "ok" and items["signin"]["status"] == "ok" and items["post"]["status"] == "todo" and "media.write" in items["post"]["detail"]
