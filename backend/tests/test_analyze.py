import json
import subprocess

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

import models  # noqa: F401
import app as appmod

OLLAMA = "http://localhost:11434/api/chat"


@pytest.fixture
def clip(tmp_path):
    p = tmp_path / "t.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=360x640:rate=15:duration=3",
                    "-pix_fmt", "yuv420p", str(p)], check=True, capture_output=True)
    return p


def reply(content):
    return httpx.Response(200, json={"message": {"content": content}})


@respx.mock
async def test_analyze_returns_platform_copy_and_sends_frames_to_vision_model(clip):
    good = json.dumps({"instagram": {"caption": "Hello", "hashtags": ["#One", "Two Words", "one"]},
                       "youtube": {"title": "T", "description": "D", "tags": ["a"]}})
    route = respx.post(OLLAMA).mock(side_effect=[reply("A test pattern."), reply(good)])
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")}, data={"lang": "en"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["meta"]["orientation"] == "vertical" and d["description"] == "A test pattern."
    assert d["copy"]["instagram"]["hashtags"] == ["One", "TwoWords"]  # cleaned and de-duplicated
    first = json.loads(route.calls[0].request.content)
    assert first["model"] == "qwen2.5vl:7b" and len(first["messages"][0]["images"]) == 6


@respx.mock
async def test_analyze_reports_missing_model_clearly(clip):
    respx.post(OLLAMA).mock(return_value=httpx.Response(404, json={"error": "not found"}))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")})
    assert r.status_code == 503 and "ollama pull" in r.json()["detail"]
