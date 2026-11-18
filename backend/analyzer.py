"""Local video analysis: frames -> vision model (what is in it) -> text model (platform copy).
Everything runs on this machine through Ollama; no video or frame leaves it."""
import json
import httpx

from config import settings

LANG = {"en": "English", "ar": "Arabic", "both": "English first, then the Arabic translation on a new line"}


class AnalyzerError(Exception):
    pass


async def _chat(model: str, messages: list, *, json_mode: bool, timeout: float) -> str:
    body = {"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.4, "num_ctx": settings.num_ctx}}
    if json_mode:
        body["format"] = "json"
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(f"{settings.ollama_url}/api/chat", json=body)
    except httpx.HTTPError as e:
        raise AnalyzerError(f"Cannot reach the local model server ({settings.ollama_url}). Is Ollama running? {e}")
    if r.status_code == 404:
        raise AnalyzerError(f"Model '{model}' is not installed. Run: ollama pull {model}")
    if r.status_code >= 400:
        raise AnalyzerError(f"Local model error {r.status_code}: {r.text[:200]}")
    return r.json()["message"]["content"]


async def describe(frames: list[str], meta: dict, hint: str) -> str:
    prompt = ("These are frames from one short video, in time order. Describe what the video shows: subject, "
              "setting, actions, mood, any visible text. Be factual and specific, 4 to 6 sentences. Do not invent "
              f"anything you cannot see. Video: {meta['duration_s']}s, {meta['orientation']}."
              + (f" Extra context from the user: {hint}" if hint else ""))
    return (await _chat(settings.vision_model, [{"role": "user", "content": prompt, "images": frames}],
                        json_mode=False, timeout=420)).strip()


def _clean_tags(tags, limit: int) -> list[str]:
    out = []
    for t in tags or []:
        t = str(t).strip().lstrip("#").replace(" ", "")
        if t and t.lower() not in [x.lower() for x in out]:
            out.append(t)
    return out[:limit]


async def write_copy(description: str, meta: dict, lang: str, hint: str) -> dict:
    short = meta["orientation"] == "vertical" and meta["duration_s"] <= 180
    prompt = f"""You write social media copy for a government communications team. Tone: clear, professional, warm.
Video description: {description}
{('User context: ' + hint) if hint else ''}
Language: {LANG.get(lang, 'English')}.
Return ONLY JSON with this exact shape:
{{"instagram": {{"caption": "<hook line + 1-2 short sentences, max 300 chars, no hashtags>", "hashtags": ["<8 to 12 relevant single-word or camel-case tags without #>"]}},
 "youtube": {{"title": "<max 90 chars, specific, no clickbait>", "description": "<2-3 sentences, max 600 chars, then a blank line and 3 hashtags>", "tags": ["<8 to 12 search keywords>"]}}}}
{'This is a vertical video under 3 minutes, so YouTube will publish it as a Short; add #Shorts to the youtube description hashtags.' if short else ''}
Only describe what the description says. Do not invent facts, names, numbers or dates."""
    raw = await _chat(settings.text_model, [{"role": "user", "content": prompt}], json_mode=True, timeout=180)
    try:
        d = json.loads(raw)
        ig, yt = d["instagram"], d["youtube"]
        hashtags = _clean_tags(ig.get("hashtags"), 30)
        return {
            "instagram": {"caption": str(ig["caption"]).strip()[:2000], "hashtags": hashtags},
            "youtube": {"title": str(yt["title"]).strip()[:100], "description": str(yt["description"]).strip()[:5000],
                        "tags": _clean_tags(yt.get("tags"), 15) or hashtags[:12]},  # small models often skip tags
        }
    except (KeyError, ValueError, TypeError):
        raise AnalyzerError("The local model returned an unusable answer. Try Regenerate.")
