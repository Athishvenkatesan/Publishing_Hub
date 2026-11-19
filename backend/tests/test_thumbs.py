import base64
import io
import json
import subprocess

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from PIL import Image

import app as appmod
import models  # noqa: F401
import thumb_render

OLLAMA = "http://localhost:11434/api/chat"


def make_clip(path, size):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=15:duration=4", "-pix_fmt", "yuv420p", str(path)],
                   check=True, capture_output=True)
    return path


@pytest.fixture
def vertical(tmp_path):
    return make_clip(tmp_path / "v.mp4", "360x640")


@pytest.fixture
def frame(tmp_path):
    p = tmp_path / "f.jpg"
    Image.effect_mandelbrot((640, 360), (-2.2, -1.2, 1.0, 1.2), 80).convert("RGB").save(p)
    return p


def dims(jpg):
    im = Image.open(io.BytesIO(jpg))
    return im.format, im.size


def test_render_gives_a_16_9_jpeg_under_2mb_in_every_style(frame):
    outs = {s: thumb_render.render(frame, "Save Water Dubai", s, logo=(s == "band")) for s in ("band", "scrim", "none")}
    for jpg in outs.values():
        assert dims(jpg) == ("JPEG", (1280, 720)) and len(jpg) < 2_000_000
    assert len({hash(j) for j in outs.values()}) == 3  # the styles really differ


def test_vertical_frames_are_placed_on_a_blurred_background(tmp_path):
    tall = tmp_path / "t.jpg"
    Image.new("RGB", (360, 640), (200, 30, 30)).save(tall)
    jpg = thumb_render.render(tall, "", "none")
    im = Image.open(io.BytesIO(jpg))
    assert im.size == (1280, 720)
    assert im.getpixel((640, 360))[0] > 150          # the sharp frame is in the middle
    assert im.getpixel((10, 360)) != im.getpixel((640, 360))  # the sides are the darkened blur


def test_arabic_and_very_long_headlines_render_without_error(frame):
    assert dims(thumb_render.render(frame, "ترشيد استهلاك المياه", "band")) == ("JPEG", (1280, 720))
    long = "Every single drop of water counts for the whole city of Dubai today"
    assert dims(thumb_render.render(frame, long, "scrim", logo=True)) == ("JPEG", (1280, 720))
    assert thumb_render.has_arabic("مياه") and not thumb_render.has_arabic("water")


@respx.mock
async def test_candidates_use_the_ai_order_and_headlines(vertical):
    rank = httpx.Response(200, json={"message": {"content": 'Sure. {"ranking": [3, 1, 2], "reason": "Clear subject"}'}})
    heads = httpx.Response(200, json={"message": {"content": json.dumps({"headlines": ["Save Water", "Every Drop Counts", "Save Water"]})}})
    route = respx.post(OLLAMA).mock(side_effect=[rank, heads])
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/thumbnails/candidates", files={"file": ("v.mp4", vertical.read_bytes(), "video/mp4")},
                         data={"description": "A water saving campaign.", "title": "T", "lang": "en"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ranked_by"] == "ai" and d["note"] == "Clear subject" and d["style"] == "band"
        assert d["headlines"] == ["Save Water", "Every Drop Counts"] and len(d["candidates"]) == 3
        first = base64.b64decode(d["candidates"][0]["image"].split(",")[1])
        assert dims(first) == ("JPEG", (1280, 720))
        assert len(json.loads(route.calls[0].request.content)["messages"][0]["images"]) >= 3  # frames went to the vision model
        # re-render with another headline, style and the logo
        rr = await c.post("/api/thumbnails/render", json={"job_id": d["job_id"], "frame_id": d["candidates"][1]["id"],
                                                          "headline": "Every Drop Counts", "style": "scrim", "logo": True})
        assert rr.status_code == 200 and rr.headers["content-type"] == "image/jpeg" and dims(rr.content) == ("JPEG", (1280, 720))


@respx.mock
async def test_candidates_still_work_when_the_local_ai_is_off(vertical):
    respx.post(OLLAMA).mock(side_effect=httpx.ConnectError("refused"))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/thumbnails/candidates", files={"file": ("v.mp4", vertical.read_bytes(), "video/mp4")},
                         data={"description": "A water saving campaign."})
    d = r.json()
    assert r.status_code == 200 and d["ranked_by"] == "sharpness" and d["headlines"] == [] and d["style"] == "none"
    assert 1 <= len(d["candidates"]) <= 3


async def test_render_rejects_expired_or_tricky_ids_and_bad_input():
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        for job, fr in (("0123456789ab", "f0"), ("../../etc", "f0"), ("0123456789ab", "../x")):
            r = await c.post("/api/thumbnails/render", json={"job_id": job, "frame_id": fr})
            assert r.status_code == 410
        bad = await c.post("/api/thumbnails/candidates", files={"file": ("a.txt", b"x", "text/plain")})
        assert bad.status_code == 422
