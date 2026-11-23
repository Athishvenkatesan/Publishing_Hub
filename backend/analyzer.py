"""Local video analysis: frames -> vision model (what is in it) -> text model (platform copy).
Everything runs on this machine through Ollama; no video or frame leaves it."""
import json
import re
import httpx

from config import settings
from youtube import CATEGORIES

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


CATEGORY_IDS = {name: cid for cid, name in CATEGORIES.items()}


def is_short(meta: dict) -> bool:
    return meta["orientation"] == "vertical" and meta["duration_s"] <= 180


CAUSE_WORDS = ("campaign", "cause", "charity", "donat", "volunteer", "awareness", "nonprofit", "non-profit", "activis", "fundrais")


def sane_category(name: str, reason: str, description: str, hint: str) -> tuple[str, str]:
    """Small models over-pick Nonprofits & Activism. Accept it only when a campaign or cause is actually mentioned."""
    if name == "Nonprofits & Activism" and not any(w in f"{description} {hint}".lower() for w in CAUSE_WORDS):
        return "People & Blogs", "Defaulted to People & Blogs: no campaign or cause is mentioned. Change it under Advanced options if needed."
    return name, reason


async def write_youtube(description: str, meta: dict, lang: str, hint: str) -> dict:
    """A fuller YouTube package than write_copy: title options, structured description, tags, hashtags, category, thumbnail ideas."""
    short = is_short(meta)
    prompt = f"""You write YouTube metadata for a government communications team. Tone: clear, professional, warm.
Video description: {description}
{('User context: ' + hint) if hint else ''}
Language: {LANG.get(lang, 'English')}.
Return ONLY JSON with this exact shape:
{{"titles": ["<3 different title options, each max 90 chars, specific, no clickbait>"],
 "summary": "<2 sentences describing the video, max 250 chars>",
 "key_points": ["<3 to 5 short bullet points, each taken from the description>"],
 "call_to_action": "<one short line inviting viewers to watch, share or follow>",
 "hashtags": ["<5 relevant single-word or camel-case tags without #>"],
 "tags": ["<10 to 15 search keywords>"],
 "category": "<exactly one of: {', '.join(CATEGORY_IDS)}. Pick the closest everyday topic. Use Nonprofits & Activism only for a campaign or cause, and People & Blogs when unsure>",
 "category_reason": "<one short sentence>",
 "thumbnail_ideas": ["<2 short thumbnail ideas using only what is visible>"]}}
Only use what the description says. Do not invent facts, names, numbers or dates."""
    raw = await _chat(settings.text_model, [{"role": "user", "content": prompt}], json_mode=True, timeout=240)
    try:
        d = json.loads(raw)
        titles = [str(t).strip()[:100] for t in d["titles"] if str(t).strip()][:3]
        if not titles:
            raise ValueError("no titles")
        hashtags = _clean_tags(d.get("hashtags"), 5)
        tags = _clean_tags(d.get("tags"), 15) or hashtags
        shown = (["Shorts"] if short else []) + hashtags
        points = [f"- {str(p).strip()}" for p in d.get("key_points", []) if str(p).strip()][:5]
        body = "\n\n".join(x for x in [str(d.get("summary", "")).strip(), "\n".join(points), str(d.get("call_to_action", "")).strip(),
                                         " ".join(f"#{h}" for h in shown[:5])] if x)
        name = d.get("category") if d.get("category") in CATEGORY_IDS else "People & Blogs"
        name, reason = sane_category(name, str(d.get("category_reason", "")).strip(), description, hint)
        ideas = [str(t).strip() for t in d.get("thumbnail_ideas", []) if str(t).strip()][:3]
        ideas = ideas or [f"A clear still showing: {p.lstrip('- ')}" for p in points[:2]]  # small models often skip these
        return {"titles": titles, "title": titles[0], "description": body[:5000], "tags": tags, "hashtags": hashtags,
                "category_id": CATEGORY_IDS[name], "category_name": name, "category_reason": reason,
                "thumbnail_ideas": ideas,
                "format": "short" if short else "video",
                "format_reason": ("Vertical and 3 minutes or less: YouTube publishes it as a Short." if short
                                  else "Not vertical, or longer than 3 minutes: YouTube publishes it as a normal video.")}
    except (KeyError, ValueError, TypeError):
        raise AnalyzerError("The local model returned an unusable answer. Try Regenerate.")


async def write_linkedin(description: str, meta: dict, lang: str, hint: str) -> dict:
    """A LinkedIn post for a video: three opening lines to choose from, the post text with hashtags, and a short video title."""
    prompt = f"""You write LinkedIn posts for a government communications team. Tone: professional, warm, plain words, no emojis, no clickbait.
Video description: {description}
{('User context: ' + hint) if hint else ''}
Language: {LANG.get(lang, 'English')}.
Return ONLY JSON with this exact shape:
{{"hooks": ["<3 different opening lines, each max 120 chars>"],
 "body": "<2 short paragraphs, then one line inviting people to watch or share; max 900 chars; no hashtags>",
 "hashtags": ["<3 to 5 relevant single-word or camel-case tags without #>"],
 "title": "<video title, max 70 chars>"}}
Only use what the description says. Do not invent facts, names, numbers or dates."""
    raw = await _chat(settings.text_model, [{"role": "user", "content": prompt}], json_mode=True, timeout=180)
    try:
        d = json.loads(raw)
        hooks = [str(h).strip()[:150] for h in d["hooks"] if str(h).strip()][:3]
        body = str(d["body"]).strip()
        if not hooks or not body:
            raise ValueError("empty")
        tags = _clean_tags(d.get("hashtags"), 5)
        text = "\n\n".join(x for x in [hooks[0], body, " ".join(f"#{t}" for t in tags)] if x)
        return {"hooks": hooks, "body": body, "hashtags": tags, "text": text[:3000], "title": str(d.get("title") or hooks[0]).strip()[:100]}
    except (KeyError, ValueError, TypeError):
        raise AnalyzerError("The local model returned an unusable answer. Try Regenerate.")


async def write_x(description: str, meta: dict, lang: str, hint: str) -> dict:
    """Three ready-to-post X texts for a video, each short enough for a normal account (280 characters)."""
    prompt = f"""You write posts on X for a government communications team. Tone: clear, warm, plain words, no clickbait, at most one emoji.
Video description: {description}
{('User context: ' + hint) if hint else ''}
Language: {LANG.get(lang, 'English')}.
Return ONLY JSON with this exact shape:
{{"posts": ["<3 different posts, each at most 240 characters including 1 or 2 hashtags at the end>"]}}
Only use what the description says. Do not invent facts, names, numbers or dates."""
    raw = await _chat(settings.text_model, [{"role": "user", "content": prompt}], json_mode=True, timeout=180)
    try:
        posts = [str(p).strip()[:280] for p in json.loads(raw)["posts"] if str(p).strip()][:3]
        if not posts:
            raise ValueError("empty")
        return {"options": posts, "text": posts[0]}
    except (KeyError, ValueError, TypeError):
        raise AnalyzerError("The local model returned an unusable answer. Try Regenerate.")


def json_in(text: str) -> dict:
    """The first JSON object in a model reply. Vision models often wrap it in prose or code fences."""
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


async def classify(frames: list[str], meta: dict, hint: str) -> dict | None:
    """Ask the vision model two things about the video: is it for children, and does it look AI-generated. None if it gives nothing usable."""
    prompt = ("These are frames from one short video, in time order. Answer two questions about the video as a whole. "
              "1) for_kids: is it MADE FOR CHILDREN as the audience (cartoon characters, toys, nursery rhymes, children's learning)? "
              "Children merely appearing in it does not count. "
              "2) ai_generated: does it look AI-generated or computer-generated rather than filmed with a camera "
              "(unnatural or warped motion, impossible detail, over-smooth or surreal look, garbled text)? Real camera footage of real places is false. "
              'Judge only from the pictures. Reply ONLY with JSON: {"for_kids": true|false, "kids_confidence": "high|medium|low", "kids_reason": "<short>", '
              '"ai_generated": true|false, "ai_confidence": "high|medium|low", "ai_reason": "<short>"}')
    try:
        raw = await _chat(settings.vision_model, [{"role": "user", "content": prompt, "images": frames}], json_mode=False, timeout=300)
        d = json_in(raw)
    except (AnalyzerError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(d, dict) or "ai_generated" not in d:
        return None
    return {"for_kids": bool(d.get("for_kids")), "kids_confidence": str(d.get("kids_confidence", "low")).lower(), "kids_reason": str(d.get("kids_reason", ""))[:160],
            "ai_generated": bool(d.get("ai_generated")), "ai_confidence": str(d.get("ai_confidence", "low")).lower(), "ai_reason": str(d.get("ai_reason", ""))[:160]}


async def write_meta(description: str, meta: dict, lang: str, hint: str) -> dict:
    """A Facebook Page post for a video: three title options, the post text with hashtags, and a short caption for Instagram and Threads."""
    prompt = f"""You write Facebook Page posts for a government communications team. Tone: clear, warm, plain words, no clickbait, at most two emojis.
Video description: {description}
{('User context: ' + hint) if hint else ''}
Language: {LANG.get(lang, 'English')}.
Return ONLY JSON with this exact shape:
{{"titles": ["<3 different video titles, each max 80 chars>"],
 "body": "<1 or 2 short paragraphs about the video, max 700 chars, no hashtags>",
 "hashtags": ["<3 to 6 relevant single-word or camel-case tags without #>"],
 "caption": "<one short caption for Instagram and Threads, max 300 chars, no hashtags>"}}
Only use what the description says. Do not invent facts, names, numbers or dates."""
    raw = await _chat(settings.text_model, [{"role": "user", "content": prompt}], json_mode=True, timeout=180)
    try:
        d = json.loads(raw)
        titles = [str(t).strip()[:100] for t in d["titles"] if str(t).strip()][:3]
        body = str(d["body"]).strip()
        if not titles or not body:
            raise ValueError("empty")
        tags = _clean_tags(d.get("hashtags"), 6)
        line = " ".join(f"#{t}" for t in tags)
        caption = re.sub(r"\s*#\w+", "", str(d.get("caption") or body)).strip()[:300]  # the model sometimes adds tags anyway; they go on once, below
        return {"titles": titles, "title": titles[0], "body": body, "hashtags": tags,
                "text": "\n\n".join(x for x in [body, line] if x)[:5000], "caption": "\n\n".join(x for x in [caption, line] if x)}
    except (KeyError, ValueError, TypeError):
        raise AnalyzerError("The local model returned an unusable answer. Try Regenerate.")
