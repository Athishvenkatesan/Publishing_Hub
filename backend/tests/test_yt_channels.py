import json

import httpx
import pytest
import respx

import yt_accounts
from routes import yt_channels
from .test_youtube import TOK, client, connect_now  # noqa: F401  (shared fixtures)

G = "https://www.googleapis.com/youtube/v3/channels"
OLLAMA = "http://localhost:11434/api/chat"
ENV = """YOUTUBE_ACCOUNTS=news,kids,idle
YOUTUBE_NEWS_LABEL=news@example.com
YOUTUBE_NEWS_CLIENT_ID=news-id
YOUTUBE_NEWS_CLIENT_SECRET=news-secret
YOUTUBE_KIDS_LABEL=kids@example.com
YOUTUBE_KIDS_CLIENT_ID=kids-id
YOUTUBE_KIDS_CLIENT_SECRET=kids-secret
YOUTUBE_IDLE_LABEL=idle@example.com
YOUTUBE_IDLE_CLIENT_ID=idle-id
YOUTUBE_IDLE_CLIENT_SECRET=idle-secret
"""
CHANNELS = {
    "news": {"id": "UCN", "snippet": {"title": "Dubai Water News", "customUrl": "@dxbwater", "description": "Water saving tips and utility updates for Dubai residents", "publishedAt": "2026-01-01T00:00:00Z"},
             "statistics": {"subscriberCount": "5"}, "status": {"longUploadsStatus": "allowed", "madeForKids": False}, "brandingSettings": {"channel": {"keywords": "water saving dubai utility"}}},
    "kids": {"id": "UCK", "snippet": {"title": "Gen Video AI for Kids", "customUrl": "@genkids", "description": "Cartoons and songs for children", "publishedAt": "2026-01-01T00:00:00Z"},
             "statistics": {}, "status": {"longUploadsStatus": "allowed", "madeForKids": True}, "brandingSettings": {"channel": {"keywords": "kids cartoons songs"}}},
}


@pytest.fixture(autouse=True)
def three(client, tmp_path, monkeypatch):  # after `client`, which resets the .env path
    env = tmp_path / "three.env"
    env.write_text(ENV)
    monkeypatch.setattr(yt_accounts, "ENV_FILE", env)
    yt_channels._cache.clear()
    connect_now("news")
    connect_now("kids")  # "idle" stays signed out

    def token(request):
        who = request.content.decode().split("client_id=")[1].split("-id")[0]
        return httpx.Response(200, json={"access_token": f"AT-{who}"})

    respx.post(TOK).mock(side_effect=token)
    respx.get(G).mock(side_effect=lambda r: httpx.Response(200, json={"items": [CHANNELS[r.headers["authorization"].split("AT-")[-1]]]}))


def text_model(picks):
    return httpx.Response(200, json={"message": {"content": json.dumps({"picks": picks})}})


@respx.mock
async def test_profiles_only_cover_signed_in_channels_and_spot_kids_channels(client):
    d = (await client.get("/api/youtube/channels/profiles")).json()["profiles"]
    assert sorted(p["key"] for p in d) == ["kids", "news"]  # the signed-out account is left out
    kids = next(p for p in d if p["key"] == "kids")
    assert kids["kids_channel"] is True and kids["title"] == "Gen Video AI for Kids" and next(p for p in d if p["key"] == "news")["kids_channel"] is False
    assert next(p for p in d if p["key"] == "news")["verified"] is True


@respx.mock
async def test_a_kids_video_goes_to_the_kids_channel_and_a_general_one_stays_off_it(client):
    respx.post(OLLAMA).mock(return_value=text_model([{"key": "news", "score": 9, "reason": "water topic"}, {"key": "kids", "score": 7, "reason": "friendly tone"}]))
    r = await client.post("/api/youtube/channels/suggest", json={"title": "Save water", "description": "Tips to save water at home", "kids": False})
    assert r.json()["recommended"] == ["news"] and r.json()["by"] == "ai"  # a kids channel is not suggested for a general video
    r = await client.post("/api/youtube/channels/suggest", json={"title": "Bear song", "description": "A cartoon bear sings about water", "kids": True})
    assert r.json()["recommended"] == ["kids"]


@respx.mock
async def test_without_the_ai_the_words_decide(client):
    respx.post(OLLAMA).mock(side_effect=httpx.ConnectError("refused"))
    r = await client.post("/api/youtube/channels/suggest", json={"title": "Water saving in Dubai", "description": "Utility tips for residents", "kids": False})
    d = r.json()
    assert d["by"] == "keywords" and d["recommended"] == ["news"] and d["ranked"][0]["reason"].startswith("shares the words")
    none = await client.post("/api/youtube/channels/suggest", json={"title": "Zebra", "description": "Striped animals", "kids": False})
    assert none.json()["recommended"] == []  # nothing fits: tick nothing and let the user choose


@respx.mock
async def test_one_signed_in_channel_is_simply_chosen(client):
    yt_accounts.token_path("kids").unlink()
    yt_channels._cache.clear()
    d = (await client.post("/api/youtube/channels/suggest", json={"title": "x", "description": "y"})).json()
    assert d["recommended"] == ["news"] and d["by"] == "only"


@respx.mock
async def test_a_kids_video_always_goes_to_the_kids_channel_even_if_the_ai_forgot_to_score_it(client):
    respx.post(OLLAMA).mock(return_value=text_model([{"key": "news", "score": 9, "reason": "topic"}]))  # the kids channel is missing from the AI answer
    d = (await client.post("/api/youtube/channels/suggest", json={"title": "Bear song", "description": "cartoon bear", "kids": True})).json()
    assert d["recommended"] == ["kids"]
    assert next(r for r in d["ranked"] if r["key"] == "kids")["reason"] == "a kids channel, and this video is made for kids"
