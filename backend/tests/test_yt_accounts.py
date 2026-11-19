import io
import json
from urllib.parse import parse_qs, urlparse

import httpx
import respx

import yt_accounts
import youtube
from .test_youtube import TOK, UP, VID, client, connect_now, video  # noqa: F401  (shared fixtures)

ENV = """YOUTUBE_ACCOUNTS=dgm,athish
YOUTUBE_DGM_LABEL=dgm@example.com
YOUTUBE_DGM_CLIENT_ID=dgm-id
YOUTUBE_DGM_CLIENT_SECRET=dgm-secret
YOUTUBE_ATHISH_LABEL=athish@example.com
YOUTUBE_ATHISH_CLIENT_ID=athish-id
YOUTUBE_ATHISH_CLIENT_SECRET=athish-secret
"""


def two_accounts(tmp_path, monkeypatch):
    f = tmp_path / "two.env"
    f.write_text(ENV)
    monkeypatch.setattr(yt_accounts, "ENV_FILE", f)


async def test_accounts_list_shows_each_one_and_whether_it_is_signed_in(client, tmp_path, monkeypatch):
    two_accounts(tmp_path, monkeypatch)
    connect_now("athish")
    d = (await client.get("/api/youtube/accounts")).json()
    assert d["default"] == "dgm"
    assert [(a["key"], a["label"], a["connected"]) for a in d["accounts"]] == [("dgm", "dgm@example.com", False), ("athish", "athish@example.com", True)]
    assert (await client.get("/api/youtube/status", params={"account": "nope"})).status_code == 404


async def test_an_account_with_missing_values_says_what_is_missing(client, tmp_path, monkeypatch):
    f = tmp_path / "bad.env"
    f.write_text("YOUTUBE_ACCOUNTS=half\nYOUTUBE_HALF_CLIENT_ID=only-id\n")
    monkeypatch.setattr(yt_accounts, "ENV_FILE", f)
    a = (await client.get("/api/youtube/accounts")).json()["accounts"][0]
    assert a["configured"] is False and "YOUTUBE_HALF_CLIENT_SECRET" in a["missing"]
    r = await client.get("/api/youtube/connect", params={"account": "half"})
    assert r.status_code == 400 and "YOUTUBE_HALF_CLIENT_ID" in r.json()["detail"]


async def test_each_account_signs_in_with_its_own_client_and_keeps_its_own_token(client, tmp_path, monkeypatch):
    two_accounts(tmp_path, monkeypatch)
    url = (await client.get("/api/youtube/connect", params={"account": "athish"})).json()["url"]
    q = parse_qs(urlparse(url).query)
    assert q["client_id"] == ["athish-id"]
    sent = {}
    with respx.mock:
        def token(request):
            sent.update(dict(x.split("=") for x in request.content.decode().split("&")))
            return httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT-ATHISH"})
        respx.post(TOK).mock(side_effect=token)
        r = await client.get("/api/youtube/callback", params={"code": "abc", "state": q["state"][0]})
    assert sent["client_id"] == "athish-id" and sent["client_secret"] == "athish-secret"
    assert r.headers["location"].endswith("connected=1&account=athish")
    assert json.loads(yt_accounts.token_path("athish").read_text())["refresh_token"] == "RT-ATHISH"
    assert not yt_accounts.token_path("dgm").exists()  # the other account is untouched


@respx.mock
async def test_upload_goes_out_as_the_chosen_account_and_the_row_remembers_it(client, tmp_path, monkeypatch):
    two_accounts(tmp_path, monkeypatch)
    connect_now("dgm", "RT-DGM")
    connect_now("athish", "RT-ATHISH")
    used = []

    def token(request):
        body = request.content.decode()
        used.append(("athish" if "athish-id" in body else "dgm", "RT-ATHISH" in body))
        return httpx.Response(200, json={"access_token": "AT"})
    respx.post(TOK).mock(side_effect=token)
    respx.post(UP).mock(return_value=httpx.Response(200, headers={"location": "https://up.test/s"}))
    respx.put("https://up.test/s").mock(return_value=httpx.Response(200, json={"id": "VA"}))
    r = await client.post("/api/youtube/posts", params={"account": "athish"}, files=video(), data={"title": "T"})
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert used == [("athish", True)]  # athish's client AND athish's own refresh token
    # the row belongs to athish, so a later refresh uses athish's sign-in even when no account is asked for
    used.clear()
    respx.get(VID).mock(return_value=httpx.Response(200, json={"items": [{"status": {"uploadStatus": "processed", "privacyStatus": "public"}}]}))
    h = (await client.get("/api/youtube/posts")).json()["items"][0]
    assert h["status"] == "PUBLISHED" and h["account_name"] == "athish@example.com" and used and all(u == ("athish", True) for u in used)
    assert item["account_name"] == "athish@example.com"


async def test_old_single_pair_in_settings_still_works_as_account_main(client):
    d = (await client.get("/api/youtube/accounts")).json()
    assert [a["key"] for a in d["accounts"]] == ["main"] and d["default"] == "main"
