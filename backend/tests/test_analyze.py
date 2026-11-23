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


NO_VERDICT = "I cannot tell."  # a vision reply that is not JSON: the classification is simply skipped


def by_model(vision, text):
    """Answer each Ollama call by which model it is for. `vision` and `text` are the replies in order."""
    vision, text = list(vision), list(text)

    def handler(request):
        model = json.loads(request.content)["model"]
        return (vision if model == "qwen2.5vl:7b" else text).pop(0)
    return handler


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


@respx.mock
async def test_analyze_youtube_returns_a_full_package(clip):
    pkg = json.dumps({"titles": ["One", "Two", "Three"], "summary": "A test pattern.", "key_points": ["Colours", "Numbers"],
                      "call_to_action": "Watch now.", "hashtags": ["#Test", "Pattern"], "tags": ["a", "b"],
                      "category": "Education", "category_reason": "It teaches.", "thumbnail_ideas": ["Big colours"]})
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A test pattern."), reply(NO_VERDICT)], [reply(pkg)]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/youtube", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")}, data={"lang": "en"})
    assert r.status_code == 200, r.text
    y = r.json()["youtube"]
    assert y["titles"] == ["One", "Two", "Three"] and y["title"] == "One" and y["category_id"] == "27"
    assert y["format"] == "short" and "#Shorts" in y["description"] and "- Colours" in y["description"]
    assert y["hashtags"] == ["Test", "Pattern"] and y["thumbnail_ideas"] == ["Big colours"]


@respx.mock
async def test_analyze_youtube_unknown_category_falls_back(clip):
    pkg = json.dumps({"titles": ["One"], "summary": "S", "key_points": [], "call_to_action": "", "hashtags": [], "tags": [],
                      "category": "Cooking", "category_reason": "", "thumbnail_ideas": []})
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A test pattern."), reply(NO_VERDICT)], [reply(pkg)]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/youtube", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")})
    assert r.json()["youtube"]["category_name"] == "People & Blogs"


@respx.mock
async def test_analyze_youtube_fills_thumbnail_ideas_when_the_model_skips_them(clip):
    pkg = json.dumps({"titles": ["One"], "summary": "S", "key_points": ["Calm waves", "Soft light"], "call_to_action": "",
                      "hashtags": [], "tags": [], "category": "Travel & Events", "category_reason": "", "thumbnail_ideas": []})
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A test pattern."), reply(NO_VERDICT)], [reply(pkg)]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/youtube", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")})
    assert r.json()["youtube"]["thumbnail_ideas"] == ["A clear still showing: Calm waves", "A clear still showing: Soft light"]


@respx.mock
async def test_nonprofit_category_needs_a_cause_in_the_text(clip):
    pkg = json.dumps({"titles": ["One"], "summary": "S", "key_points": [], "call_to_action": "", "hashtags": [], "tags": [],
                      "category": "Nonprofits & Activism", "category_reason": "peace", "thumbnail_ideas": ["x"]})
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A calm ocean."), reply(NO_VERDICT), reply("A water saving campaign."), reply(NO_VERDICT)], [reply(pkg), reply(pkg)]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        plain = await c.post("/api/analyze/youtube", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")})
        cause = await c.post("/api/analyze/youtube", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")})
    assert plain.json()["youtube"]["category_name"] == "People & Blogs" and "Defaulted" in plain.json()["youtube"]["category_reason"]
    assert cause.json()["youtube"]["category_name"] == "Nonprofits & Activism"


PKG = json.dumps({"titles": ["One"], "summary": "S", "key_points": [], "call_to_action": "", "hashtags": [], "tags": [],
                  "category": "Education", "category_reason": "", "thumbnail_ideas": ["x"]})


async def analyse(clip, vision_verdict, hint="", path=None):
    p = path or clip
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A cartoon bear sings."), reply(vision_verdict)], [reply(PKG)]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/youtube", files={"file": ("t.mp4", p.read_bytes(), "video/mp4")}, data={"hint": hint})
    assert r.status_code == 200, r.text
    return r.json()["youtube"]["suggestions"]


@respx.mock
async def test_the_model_can_tick_made_for_kids_and_ai_content(clip):
    verdict = json.dumps({"for_kids": True, "kids_confidence": "high", "kids_reason": "cartoon bear singing a nursery rhyme",
                          "ai_generated": True, "ai_confidence": "medium", "ai_reason": "smooth, surreal motion"})
    s = await analyse(clip, verdict)
    assert s["made_for_kids"]["value"] is True and "nursery rhyme" in s["made_for_kids"]["reason"]
    assert s["ai_generated"]["value"] is True and "surreal" in s["ai_generated"]["reason"]


@respx.mock
async def test_a_low_confidence_guess_does_not_tick_anything(clip):
    verdict = json.dumps({"for_kids": True, "kids_confidence": "low", "ai_generated": True, "ai_confidence": "low"})
    s = await analyse(clip, verdict)
    assert s["made_for_kids"]["value"] is False and "tick it yourself" in s["made_for_kids"]["reason"]
    assert s["ai_generated"]["value"] is False and "No sign of AI" in s["ai_generated"]["reason"]


@respx.mock
async def test_the_context_note_and_file_labels_count_even_when_the_model_says_nothing(clip, tmp_path):
    s = await analyse(clip, NO_VERDICT, hint="Made with Sora for kids")
    assert s["ai_generated"]["value"] and "context note" in s["ai_generated"]["reason"] and s["made_for_kids"]["value"]
    labelled = tmp_path / "labelled.mp4"
    labelled.write_bytes(clip.read_bytes() + b"<Iptc4xmpExt:DigitalSourceType>trainedAlgorithmicMedia</Iptc4xmpExt:DigitalSourceType>")
    s = await analyse(clip, NO_VERDICT, path=labelled)
    assert s["ai_generated"]["value"] and "metadata says it was made by an AI model" in s["ai_generated"]["reason"]
    tagged = tmp_path / "tagged.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", str(clip), "-c", "copy", "-metadata", "comment=Created with Runway Gen-3", str(tagged)], check=True, capture_output=True)
    s = await analyse(clip, NO_VERDICT, path=tagged)
    assert s["ai_generated"]["value"] and "runway" in s["ai_generated"]["reason"].lower()


@respx.mock
async def test_analyze_linkedin_returns_hooks_text_and_a_title(clip):
    pkg = json.dumps({"hooks": ["First line", "Second line", "Third line"], "body": "Para one.\n\nPara two. Watch and share.",
                      "hashtags": ["#Water", "Dubai"], "title": "Water saving"})
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A test pattern.")], [reply(pkg)]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/linkedin", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")}, data={"lang": "en"})
    assert r.status_code == 200, r.text
    li = r.json()["linkedin"]
    assert li["hooks"] == ["First line", "Second line", "Third line"] and li["title"] == "Water saving" and li["hashtags"] == ["Water", "Dubai"]
    assert li["text"] == "First line\n\nPara one.\n\nPara two. Watch and share.\n\n#Water #Dubai"


@respx.mock
async def test_analyze_x_returns_three_short_posts(clip):
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A test pattern.")], [reply(json.dumps({"posts": ["One #A", "Two #B", "x" * 400]}))]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/x", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")}, data={"lang": "en"})
    assert r.status_code == 200, r.text
    x = r.json()["x"]
    assert x["options"][:2] == ["One #A", "Two #B"] and len(x["options"][2]) == 280 and x["text"] == "One #A"


@respx.mock
async def test_analyze_all_watches_once_and_writes_all_four_posts(clip):
    yt = json.dumps({"titles": ["One", "Two"], "summary": "S.", "key_points": ["K"], "call_to_action": "Go.", "hashtags": ["Test"],
                     "tags": ["a"], "category": "Education", "category_reason": "r", "thumbnail_ideas": ["Big"]})
    li = json.dumps({"hooks": ["H1", "H2", "H3"], "body": "Body.", "hashtags": ["Water"], "title": "Water"})
    xp = json.dumps({"posts": ["X one #A", "X two #B", "X three #C"]})
    fb = json.dumps({"titles": ["FB one"], "body": "FB body.", "hashtags": ["Water"], "caption": "Short."})
    route = respx.post(OLLAMA).mock(side_effect=by_model([reply("A test pattern."), reply(NO_VERDICT)], [reply(yt), reply(li), reply(xp), reply(fb)]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/all", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")}, data={"lang": "en"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["youtube"]["title"] == "One" and d["linkedin"]["title"] == "Water" and d["x"]["text"] == "X one #A"
    assert d["facebook"]["title"] == "FB one" and d["facebook"]["caption"] == "Short.\n\n#Water"
    vision_calls = [c for c in route.calls if json.loads(c.request.content)["model"] == "qwen2.5vl:7b"]
    assert len(vision_calls) == 2  # describe + classify, once for the whole video


@respx.mock
async def test_analyze_all_reports_a_missing_model(clip):
    respx.post(OLLAMA).mock(return_value=httpx.Response(404, json={"error": "not found"}))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/all", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")})
    assert r.status_code == 503


@respx.mock
async def test_analyze_meta_returns_titles_post_text_and_caption(clip):
    pkg = json.dumps({"titles": ["Save water", "Every drop", ""], "body": "A short clip about saving water.",
                      "hashtags": ["#Water", "Dubai", "water"], "caption": "Every drop counts. #Water"})
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A test pattern.")], [reply(pkg)]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/meta", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")}, data={"lang": "en"})
    assert r.status_code == 200, r.text
    fb = r.json()["facebook"]
    assert fb["titles"] == ["Save water", "Every drop"] and fb["title"] == "Save water" and fb["hashtags"] == ["Water", "Dubai"]
    assert fb["text"] == "A short clip about saving water.\n\n#Water #Dubai" and fb["caption"] == "Every drop counts.\n\n#Water #Dubai"


@respx.mock
async def test_analyze_meta_bad_answer_asks_to_regenerate(clip):
    respx.post(OLLAMA).mock(side_effect=by_model([reply("A test pattern.")], [reply(json.dumps({"titles": [], "body": ""}))]))
    async with AsyncClient(transport=ASGITransport(app=appmod.app), base_url="http://t") as c:
        r = await c.post("/api/analyze/meta", files={"file": ("t.mp4", clip.read_bytes(), "video/mp4")}, data={"lang": "en"})
    assert r.status_code == 503 and "Regenerate" in r.json()["detail"]
