import io
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx

import yt_accounts
import yt_thumbnail
from .test_youtube import TOK, UP, client, connect_now, video  # noqa: F401  (shared fixtures)

ENV = """YOUTUBE_ACCOUNTS=dgm,second
YOUTUBE_DGM_LABEL=dgm@example.com
YOUTUBE_DGM_CLIENT_ID=dgm-id
YOUTUBE_DGM_CLIENT_SECRET=dgm-secret
YOUTUBE_SECOND_LABEL=second@example.com
YOUTUBE_SECOND_CLIENT_ID=second-id
YOUTUBE_SECOND_CLIENT_SECRET=second-secret
"""


@pytest.fixture(autouse=True)
def two(client, tmp_path, monkeypatch):  # runs after `client`, which resets the .env path
    env = tmp_path / "two.env"
    env.write_text(ENV)
    monkeypatch.setattr(yt_accounts, "ENV_FILE", env)
    monkeypatch.setattr(yt_thumbnail, "PENDING", tmp_path / "pending")


def mock_google():
    """Each account's token request answers with its own access token; each upload goes to its own session and returns its own video id."""
    metas = {}

    def token(request):
        body = request.content.decode()
        who = "second" if "second-id" in body else "dgm"
        return httpx.Response(200, json={"access_token": f"AT-{who}"})

    def init(request):
        who = request.headers["authorization"].split("AT-")[-1]
        metas[who] = json.loads(request.content)
        return httpx.Response(200, headers={"location": f"https://up.test/{who}"})

    respx.post(TOK).mock(side_effect=token)
    respx.post(UP).mock(side_effect=init)
    respx.get("https://www.googleapis.com/youtube/v3/videos").mock(  # the history refresh: YouTube is still processing
        return_value=httpx.Response(200, json={"items": [{"status": {"uploadStatus": "uploaded", "privacyStatus": "public"}}]}))
    respx.put(url__startswith="https://up.test/").mock(side_effect=lambda r: httpx.Response(200, json={"id": "V-" + r.url.path.strip("/")}))
    return metas


@respx.mock
async def test_one_video_goes_to_both_accounts_at_the_same_scheduled_moment(client, monkeypatch):
    connect_now("dgm", "RT-DGM")
    connect_now("second", "RT-SECOND")
    metas = mock_google()
    started = []
    monkeypatch.setattr(yt_thumbnail, "start", lambda a, v: started.append((a, v)))
    when = (datetime.now(ZoneInfo("Asia/Dubai")) + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
    files = {**video(), "thumbnail": ("t.png", io.BytesIO(b"p" * 50), "image/png")}
    r = await client.post("/api/youtube/posts/multi", files=files, data={
        "title": "One video", "description": "Same text", "tags": "a, b", "mode": "schedule", "scheduled_at": when, "tz": "Asia/Dubai",
        "accounts": ["dgm", "second"], "category_id": "27"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["errors"] == [] and d["thumbnail"] == "pending"
    rows = {i["account_name"]: i for i in d["items"]}
    assert set(rows) == {"dgm@example.com", "second@example.com"}
    assert all(i["status"] == "SCHEDULED" and i["mode"] == "schedule" for i in d["items"])
    # same details and the very same publish moment for both
    assert metas["dgm"]["status"]["publishAt"] == metas["second"]["status"]["publishAt"] and metas["dgm"]["status"]["privacyStatus"] == "private"
    assert metas["dgm"]["snippet"] == metas["second"]["snippet"] and metas["dgm"]["snippet"]["categoryId"] == "27"
    # each account got its own thumbnail file and its own delayed job
    assert {f.name for f in (yt_thumbnail.PENDING).iterdir()} == {"dgm~V-dgm.png", "second~V-second.png"}
    assert sorted(started) == [("dgm", "V-dgm"), ("second", "V-second")]
    hist = (await client.get("/api/youtube/posts")).json()["items"]
    assert {h["group_id"] for h in hist} == {d["items"][0]["group_id"]} and len(hist) == 2  # one submission, two rows


@respx.mock
async def test_one_account_failing_does_not_stop_the_other(client):
    connect_now("dgm", "RT-DGM")  # the second account is not signed in
    mock_google()
    r = await client.post("/api/youtube/posts/multi", files=video(), data={"title": "T", "accounts": ["dgm", "second"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert [i["account_name"] for i in d["items"]] == ["dgm@example.com"] and d["items"][0]["status"] == "PUBLISHING"
    assert d["errors"] == [{"account": "second", "label": "second@example.com", "error": "YouTube is not connected for this account. Press Connect YouTube first."}]
    assert len((await client.get("/api/youtube/posts")).json()["items"]) == 1  # no row for the one that failed


async def test_choose_at_least_one_known_account(client):
    for accounts, text in (([], "at least one"), (["ghost"], "Unknown YouTube account: ghost")):
        r = await client.post("/api/youtube/posts/multi", files=video(), data={"title": "T", "accounts": accounts} if accounts else {"title": "T"})
        assert r.status_code == 422, (accounts, r.text)
    r = await client.post("/api/youtube/posts/multi", files=video(), data={"title": "T", "accounts": ["dgm", "dgm "]})
    assert r.status_code == 200 and len(r.json()["items"]) + len(r.json()["errors"]) == 1  # the same account twice counts once
