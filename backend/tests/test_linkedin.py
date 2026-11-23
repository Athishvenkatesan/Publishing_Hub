import io
import json
import stat
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

import li_accounts
import linkedin
from .test_youtube import client  # noqa: F401  (shared database + app fixture)

AUTH, TOKEN, ME = linkedin.AUTH, linkedin.TOKEN, "https://api.linkedin.com/v2/userinfo"
VIDS, POSTS = "https://api.linkedin.com/rest/videos", "https://api.linkedin.com/rest/posts"
UPLOAD = "https://www.linkedin.com/dms-uploads/V1/uploadedVideo?sau=x"
LOGIN_PAGE = "<html>Sign in to LinkedIn</html>"
MISMATCH = "<html>Bummer, something went wrong. The redirect_uri does not match the registered value</html>"


@pytest.fixture(autouse=True)
def stores(client, tmp_path, monkeypatch):  # never touch the real accounts file or sign-ins
    monkeypatch.setattr(li_accounts, "ACCOUNTS_FILE", tmp_path / "li_accounts.json")
    monkeypatch.setattr(li_accounts, "TOKENS_DIR", tmp_path / "li_tokens")

    async def instant(_):
        return None
    monkeypatch.setattr(linkedin.asyncio, "sleep", instant)


def add(label="a@example.com", cid="78abcdefgh1234", secret="WPL_AP1.secret-value"):
    return li_accounts.add(label, cid, secret)


def sign_in(key, sub="SUB1", scope="openid profile email w_member_social", days=30):
    p = li_accounts.token_path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"access_token": f"AT-{key}", "expires_at": int(time.time()) + days * 86400, "scope": scope, "sub": sub,
                             "name": f"Name {key}", "email": f"{key}@example.com"}))


def clip():
    return {"file": ("clip.mp4", io.BytesIO(b"x" * 2048), "video/mp4")}


def mock_upload(video="urn:li:video:V1", post="urn:li:share:P1", etag='"abc123"'):
    init = respx.post(f"{VIDS}?action=initializeUpload").mock(return_value=httpx.Response(200, json={"value": {
        "video": video, "uploadToken": "TOK", "uploadInstructions": [{"firstByte": 0, "lastByte": 4194303, "uploadUrl": UPLOAD}]}}))
    put = respx.put(UPLOAD).mock(return_value=httpx.Response(200, headers={"etag": etag}))
    fin = respx.post(f"{VIDS}?action=finalizeUpload").mock(return_value=httpx.Response(200, json={}))
    respx.get(url__regex=r"https://api\.linkedin\.com/rest/videos/.+").mock(return_value=httpx.Response(200, json={"status": "AVAILABLE"}))
    created = respx.post(POSTS).mock(return_value=httpx.Response(201, headers={"x-restli-id": post}))
    return init, put, fin, created


# ---------- text, accounts ----------
def test_reserved_characters_are_escaped_but_hashtags_survive():
    out = linkedin.escape_text("Save (10%) @team_a, see #Water_Saving and #Dubai2026 now* ~ok")
    assert out == r"Save \(10%\) \@team\_a, see #Water_Saving and #Dubai2026 now\* \~ok"
    assert linkedin.escape_text("a # b") == r"a \# b"


def test_account_store_validates_slugs_reuses_and_protects_the_file():
    a = li_accounts.add("Athish.V@gmail.com", "78abcdefgh1234", "WPL_AP1.secret-value")
    assert a.key == "athishv" and a.configured and stat.S_IMODE(li_accounts.ACCOUNTS_FILE.stat().st_mode) == 0o600
    for bad in (("", "78abcdefgh1234", "WPL_AP1.secret-value"), ("x", "short", "WPL_AP1.secret-value"), ("x", "78abcdefgh1234", "tiny")):
        with pytest.raises(ValueError):
            li_accounts.add(*bad)
    b = li_accounts.add("Second", client_from="athishv")
    assert b.client_id == a.client_id and b.client_from == "athishv" and li_accounts.add("Athish.V@x.com", "78abcdefgh1234", "WPL_AP1.secret-value").key == "athishv2"
    with pytest.raises(ValueError):
        li_accounts.remove("athishv")  # another account shares its app
    li_accounts.remove("second")
    assert "second" not in li_accounts.load()


# ---------- sign-in ----------
@respx.mock
async def test_status_reads_what_linkedin_says_about_the_redirect_address(client):
    add()
    respx.get(AUTH).mock(return_value=httpx.Response(200, text=MISMATCH))
    d = (await client.get("/api/linkedin/status")).json()
    assert d["configured"] and not d["connected"] and "Authorized redirect URLs" in d["setup_problem"] and "/api/linkedin/callback" in d["setup_problem"]
    assert "Client ID 78abcdefgh1234" in d["setup_problem"]  # names the exact app to open, in case there are several
    respx.get(AUTH).mock(return_value=httpx.Response(200, text="<html>The passed in client_id is invalid &quot;x&quot;</html>"))
    assert "does not recognise this client ID" in (await client.get("/api/linkedin/status")).json()["setup_problem"]
    respx.get(AUTH).mock(return_value=httpx.Response(200, text=LOGIN_PAGE))
    assert (await client.get("/api/linkedin/status")).json()["setup_problem"] == ""


@respx.mock
async def test_an_app_that_lists_only_the_page_address_still_signs_in(client):
    add()
    page = linkedin.settings.frontend_url

    def by_redirect(request):
        return httpx.Response(200, text=LOGIN_PAGE if parse_qs(request.url.query.decode())["redirect_uri"] == [page] else MISMATCH)
    respx.get(AUTH).mock(side_effect=by_redirect)
    d = (await client.get("/api/linkedin/connect", params={"check": "true"})).json()
    assert parse_qs(urlparse(d["url"]).query)["redirect_uri"] == [page] and d["redirect_uri"] == page


async def test_connect_then_callback_saves_the_sign_in_and_forged_states_fail(client):
    add()
    url = (await client.get("/api/linkedin/connect")).json()["url"]
    q = parse_qs(urlparse(url).query)
    assert q["client_id"] == ["78abcdefgh1234"] and q["state"][0].startswith("linkedin-") and "w_member_social" in q["scope"][0] and "openid" in q["scope"][0]
    with respx.mock:
        tok = respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "AT", "expires_in": 5184000, "scope": "openid,profile,email,w_member_social"}))
        respx.get(ME).mock(return_value=httpx.Response(200, json={"sub": "SUB9", "name": "Ada L", "email": "ada@example.com"}))
        r = await client.get("/api/linkedin/callback", params={"code": "abc", "state": q["state"][0]})
    assert r.status_code == 307 and r.headers["location"].endswith("#/linkedin?connected=1&account=a")
    form = parse_qs(tok.calls[0].request.content.decode())
    assert form["grant_type"] == ["authorization_code"] and form["client_secret"] == ["WPL_AP1.secret-value"] and form["redirect_uri"] == [linkedin.settings.linkedin_redirect_uri]
    li_accounts.use("a")
    assert linkedin.connected() and linkedin.saved()["sub"] == "SUB9" and stat.S_IMODE(li_accounts.token_path("a").stat().st_mode) == 0o600
    assert "error=" in (await client.get("/api/linkedin/callback", params={"code": "abc", "state": "forged"})).headers["location"]
    scope = (await client.get("/api/linkedin/callback", params={"error": "unauthorized_scope_error", "state": "x"})).headers["location"]
    assert "Share%20on%20LinkedIn" in scope


async def test_a_sign_in_that_ran_out_counts_as_signed_out(client):
    add()
    sign_in("a", days=-1)
    d = (await client.get("/api/linkedin/accounts")).json()["accounts"][0]
    assert d["connected"] is False and d["expired"] is True


# ---------- posting ----------
@respx.mock
async def test_post_to_two_accounts_uploads_then_posts_with_escaped_text(client):
    add("a@example.com"); add("b@example.com", "99zzzzzzzz9999", "WPL_AP1.other-secret")
    sign_in("a", "SUBA"); sign_in("b", "SUBB")
    init, put, fin, created = mock_upload()
    r = await client.post("/api/linkedin/posts/multi", files=clip(), data={"text": "Save (water) #Dubai", "title": "Water", "visibility": "PUBLIC", "accounts": ["a", "b"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["items"]) == 2 and d["errors"] == [] and d["items"][0]["group_id"] == d["items"][1]["group_id"]
    owners = sorted(json.loads(c.request.content)["initializeUploadRequest"]["owner"] for c in init.calls)
    assert owners == ["urn:li:person:SUBA", "urn:li:person:SUBB"]
    assert json.loads(fin.calls[0].request.content)["finalizeUploadRequest"] == {"video": "urn:li:video:V1", "uploadToken": "TOK", "uploadedPartIds": ["abc123"]}
    assert put.calls[0].request.content == b"x" * 2048
    body = json.loads(created.calls[0].request.content)
    assert body["commentary"] == r"Save \(water\) #Dubai" and body["visibility"] == "PUBLIC" and body["content"]["media"] == {"id": "urn:li:video:V1", "title": "Water"}
    assert created.calls[0].request.headers["linkedin-version"] == linkedin.settings.linkedin_version
    h = (await client.get("/api/linkedin/posts")).json()["items"]
    assert len(h) == 2 and h[0]["status"] == "PUBLISHED" and h[0]["post_url"] == "https://www.linkedin.com/feed/update/urn:li:share:P1/" and h[0]["platform"] == "linkedin"
    assert (await client.get("/api/posts")).json()["items"] == []  # the Zernio screen never lists these


@respx.mock
async def test_one_account_failing_does_not_stop_the_other(client):
    add("a@example.com"); add("b@example.com", "99zzzzzzzz9999", "WPL_AP1.other-secret")
    sign_in("a"); sign_in("b")
    mock_upload()
    respx.post(f"{VIDS}?action=initializeUpload").mock(side_effect=[
        httpx.Response(401, json={"message": "Invalid access token"}),
        httpx.Response(200, json={"value": {"video": "urn:li:video:V1", "uploadToken": "", "uploadInstructions": [{"firstByte": 0, "lastByte": 4194303, "uploadUrl": UPLOAD}]}})])
    r = await client.post("/api/linkedin/posts/multi", files=clip(), data={"text": "Hello", "accounts": ["a", "b"]})
    d = r.json()
    assert len(d["items"]) == 1 and len(d["errors"]) == 1 and "sign in again" in d["errors"][0]["error"]


@pytest.mark.parametrize("data,name,msg", [
    ({"text": "  ", "accounts": ["a"]}, "clip.mp4", "post text"),
    ({"text": "x" * 3001, "accounts": ["a"]}, "clip.mp4", "3000"),
    ({"text": "Hi", "visibility": "ALL", "accounts": ["a"]}, "clip.mp4", "PUBLIC or CONNECTIONS"),
    ({"text": "Hi", "accounts": ["a"]}, "clip.mov", "MP4"),
    ({"text": "Hi", "accounts": ["nobody"]}, "clip.mp4", "Unknown LinkedIn account"),
])
async def test_bad_requests_are_refused_before_anything_is_sent(client, data, name, msg):
    add(); sign_in("a")
    r = await client.post("/api/linkedin/posts/multi", files={"file": (name, io.BytesIO(b"x" * 100), "video/mp4")}, data=data)
    assert r.status_code == 422 and msg in r.json()["detail"]


@respx.mock
async def test_edit_delete_and_remove_from_list(client):
    add(); sign_in("a")
    mock_upload()
    await client.post("/api/linkedin/posts/multi", files=clip(), data={"text": "Original", "accounts": ["a"]})
    row = (await client.get("/api/linkedin/posts")).json()["items"][0]
    assert (await client.get(f"/api/linkedin/posts/{row['id']}/details")).json()["text"] == "Original"
    upd = respx.post("https://api.linkedin.com/rest/posts/urn%3Ali%3Ashare%3AP1").mock(return_value=httpx.Response(204))
    assert (await client.patch(f"/api/linkedin/posts/{row['id']}", json={"text": "New (text)"})).status_code == 200
    assert upd.calls[0].request.headers["x-restli-method"] == "PARTIAL_UPDATE" and json.loads(upd.calls[0].request.content) == {"patch": {"$set": {"commentary": r"New \(text\)"}}}
    assert (await client.patch(f"/api/linkedin/posts/{row['id']}", json={"text": " "})).status_code == 422
    gone = respx.delete("https://api.linkedin.com/rest/posts/urn%3Ali%3Ashare%3AP1").mock(return_value=httpx.Response(404, json={"message": "gone"}))
    assert (await client.delete(f"/api/linkedin/posts/{row['id']}")).status_code == 200 and gone.called  # already gone on LinkedIn: the list is still cleaned
    assert (await client.get("/api/linkedin/posts")).json()["items"] == []
    await client.post("/api/linkedin/posts/multi", files=clip(), data={"text": "Second", "accounts": ["a"]})
    keep = respx.delete(url__regex=r".*/rest/posts/.*").mock(return_value=httpx.Response(204))
    row = (await client.get("/api/linkedin/posts")).json()["items"][0]
    assert (await client.delete(f"/api/linkedin/posts/{row['id']}/local")).status_code == 200 and not keep.called


# ---------- manager ----------
async def test_manager_hides_secrets_validates_and_lists_the_guide(client):
    r = await client.post("/api/linkedin/manager/accounts", json={"label": "a@example.com", "client_id": "78abcdefgh1234", "client_secret": "WPL_AP1.secret-value"})
    assert r.status_code == 201 and "secret" not in r.text.replace("has_secret", "") and r.json()["client_hint"] == "78abcd..."
    assert (await client.post("/api/linkedin/manager/accounts", json={"label": "x", "client_id": "bad id", "client_secret": "WPL_AP1.secret-value"})).status_code == 422
    d = (await client.get("/api/linkedin/manager/accounts")).json()
    assert d["redirect_uri"].endswith("/api/linkedin/callback") and len(d["guide"]) == 6 and "Share on LinkedIn" in d["guide"][1]["do"]
    assert (await client.patch("/api/linkedin/manager/accounts/a", json={"label": "Renamed"})).json()["label"] == "Renamed"
    assert (await client.delete("/api/linkedin/manager/accounts/a")).status_code == 200
    assert (await client.delete("/api/linkedin/manager/accounts/a")).status_code == 404


@respx.mock
async def test_checklist_walks_from_not_signed_in_to_ready(client):
    add()
    respx.get(AUTH).mock(return_value=httpx.Response(200, text=MISMATCH))
    items = {i["id"]: i for i in (await client.get("/api/linkedin/manager/accounts/a/check")).json()["items"]}
    assert items["redirect"]["status"] == "todo" and [a["kind"] for a in items["redirect"]["action"]] == ["copy", "link"]
    respx.get(AUTH).mock(return_value=httpx.Response(200, text=LOGIN_PAGE))
    items = {i["id"]: i for i in (await client.get("/api/linkedin/manager/accounts/a/check")).json()["items"]}
    assert items["redirect"]["status"] == "ok" and items["signin"]["status"] == "todo" and items["signin"]["action"]["kind"] == "connect"
    sign_in("a")
    respx.get(ME).mock(return_value=httpx.Response(200, json={"sub": "S", "name": "Ada", "email": "ada@example.com"}))
    items = {i["id"]: i for i in (await client.get("/api/linkedin/manager/accounts/a/check")).json()["items"]}
    assert items["signin"]["status"] == "ok" and "days left" in items["signin"]["detail"] and items["post"]["status"] == "ok"
    sign_in("a", scope="openid profile email")
    items = {i["id"]: i for i in (await client.get("/api/linkedin/manager/accounts/a/check")).json()["items"]}
    assert items["post"]["status"] == "todo" and "Share on LinkedIn" in items["post"]["detail"]
    sign_in("a", days=-2)
    items = {i["id"]: i for i in (await client.get("/api/linkedin/manager/accounts/a/check")).json()["items"]}
    assert items["signin"]["status"] == "warn" and "run out" in items["signin"]["detail"]


# ---------- sign in with a token from the portal's token generator (no redirect URL) ----------
TOKEN_TEXT = "AQV" + "x" * 60


def introspect(active=True, scope="openid,profile,email,w_member_social", status=200):
    return respx.post(linkedin.INTROSPECT).mock(return_value=httpx.Response(status, json={"active": active, "scope": scope, "expires_at": int(time.time()) + 50 * 86400}))


@respx.mock
async def test_a_token_from_the_portal_signs_the_account_in_without_any_redirect(client):
    add()
    probe = introspect()
    respx.get(ME).mock(return_value=httpx.Response(200, json={"sub": "SUBT", "name": "Tia", "email": "tia@example.com"}))
    r = await client.post("/api/linkedin/token", json={"access_token": "  " + TOKEN_TEXT[:30] + "\n" + TOKEN_TEXT[30:] + " "})  # pasted with stray spaces and a line break
    assert r.status_code == 200 and r.json()["name"] == "Tia"
    form = parse_qs(probe.calls[0].request.content.decode())
    assert form["client_id"] == ["78abcdefgh1234"] and form["client_secret"] == ["WPL_AP1.secret-value"] and form["token"] == [TOKEN_TEXT]
    li_accounts.use("a")
    t = linkedin.saved()
    assert linkedin.connected() and t["via"] == "token" and t["sub"] == "SUBT" and "w_member_social" in t["scope"] and stat.S_IMODE(li_accounts.token_path("a").stat().st_mode) == 0o600
    assert (await client.get("/api/linkedin/accounts")).json()["accounts"][0]["connected"] is True


@respx.mock
@pytest.mark.parametrize("status,active,scope,msg", [
    (200, False, "openid,profile,w_member_social", "not active for this app"),   # also what LinkedIn says for another app's token
    (200, True, "openid,profile", "w_member_social"),
    (200, True, "w_member_social", "openid, profile"),
    (401, True, "", "client secret"),
])
async def test_a_wrong_token_is_refused_with_the_reason(client, status, active, scope, msg):
    add()
    introspect(active, scope, status)
    r = await client.post("/api/linkedin/token", json={"access_token": TOKEN_TEXT})
    assert r.status_code in (400, 422) and msg in r.json()["detail"]
    li_accounts.use("a")
    assert not linkedin.connected()


async def test_a_pasted_value_that_is_clearly_not_a_token_never_reaches_linkedin(client):
    add()
    r = await client.post("/api/linkedin/token", json={"access_token": "abc"})
    assert r.status_code == 422 and "whole token" in r.json()["detail"]


@respx.mock
async def test_the_redirect_to_do_is_calm_once_a_token_has_signed_the_account_in(client):
    add()
    respx.get(AUTH).mock(return_value=httpx.Response(200, text=MISMATCH))
    respx.get(ME).mock(return_value=httpx.Response(200, json={"sub": "S", "name": "Ada", "email": ""}))
    sign_in("a")
    items = {i["id"]: i for i in (await client.get("/api/linkedin/manager/accounts/a/check")).json()["items"]}
    assert items["redirect"]["status"] == "ok" and "without it" in items["redirect"]["detail"] and items["redirect"]["action"] is None
    assert items["signin"]["status"] == "ok"


# ---------- Connect is never blocked; popup sign-in; permissions ----------
@respx.mock
async def test_connect_is_not_blocked_by_the_check_and_reports_the_problem_beside_the_link(client):
    add()
    respx.get(AUTH).mock(return_value=httpx.Response(200, text=MISMATCH))
    r = await client.get("/api/linkedin/connect", params={"check": "true", "back": "popup"})
    assert r.status_code == 200  # no 409 any more: no red console error, and LinkedIn's own page has the last word
    d = r.json()
    assert d["url"].startswith(AUTH) and "No redirect URL in your LinkedIn app" in d["problem"] and "Client ID 78abcdefgh1234" in d["problem"]
    assert parse_qs(urlparse(d["url"]).query)["redirect_uri"] == [linkedin.settings.linkedin_redirect_uri]


async def test_a_popup_sign_in_ends_on_the_page_that_closes_the_popup(client):
    add()
    url = (await client.get("/api/linkedin/connect", params={"back": "popup"})).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    with respx.mock:
        respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "AT", "expires_in": 5184000, "scope": "openid,profile,email,w_member_social"}))
        respx.get(ME).mock(return_value=httpx.Response(200, json={"sub": "S1", "name": "Ada"}))
        r = await client.get("/api/linkedin/callback", params={"code": "c", "state": state})
    assert r.headers["location"].endswith("#/linkedin/done?connected=1&account=a")


@respx.mock
async def test_a_permissions_refusal_lands_in_the_popup_and_shows_on_the_checklist(client):
    add()
    url = (await client.get("/api/linkedin/connect", params={"back": "popup"})).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    r = await client.get("/api/linkedin/callback", params={"error": "unauthorized_scope_error", "error_description": "Scope not authorized", "state": state})
    loc = r.headers["location"]
    assert "#/linkedin/done?error=" in loc and "Products%20tab" in loc and loc.endswith("&account=a")
    respx.get(AUTH).mock(return_value=httpx.Response(200, text=LOGIN_PAGE))
    items = {i["id"]: i for i in (await client.get("/api/linkedin/manager/accounts/a/check")).json()["items"]}
    assert items["permissions"]["status"] == "todo" and "Share on LinkedIn" in items["permissions"]["detail"]


@respx.mock
async def test_every_account_gets_its_own_answer(client):
    add("a@example.com"); add("b@example.com", "99zzzzzzzz9999", "WPL_AP1.other-secret")

    def by_client(request):  # app a has the redirect registered, app b does not
        ok = parse_qs(request.url.query.decode())["client_id"] == ["78abcdefgh1234"]
        return httpx.Response(200, text=LOGIN_PAGE if ok else MISMATCH)
    respx.get(AUTH).mock(side_effect=by_client)
    a = (await client.get("/api/linkedin/connect", params={"account": "a", "check": "true"})).json()
    b = (await client.get("/api/linkedin/connect", params={"account": "b", "check": "true"})).json()
    assert a["problem"] == "" and "Client ID 99zzzzzzzz9999" in b["problem"]
    assert parse_qs(urlparse(b["url"]).query)["client_id"] == ["99zzzzzzzz9999"]
