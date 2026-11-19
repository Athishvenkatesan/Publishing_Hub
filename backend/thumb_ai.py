"""Local AI for thumbnails: the vision model ranks candidate frames, the text model writes short headlines.
Both are optional: callers fall back to sharpness order and an empty headline when Ollama is off."""
import base64
import io
import json
import re
from pathlib import Path

from PIL import Image

import analyzer
from analyzer import AnalyzerError
from config import settings

HEADLINE_LANG = {"en": "English", "ar": "Arabic", "both": "two in English and one in Arabic"}


def _small_b64(path: Path, width: int = 512) -> str:
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((width, width))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()


async def rank_frames(paths: list[Path]) -> tuple[list[int], str] | None:
    """Best-to-worst order of the frames (0-based) and a short reason, or None when the model gives nothing usable."""
    prompt = (f"These are {len(paths)} numbered candidate frames (1 to {len(paths)}, in the order given) from one video. "
              "Choose the best ones for a YouTube thumbnail: a clear main subject, sharp, well lit, balanced composition, "
              "nothing awkward such as half-closed eyes or motion blur. "
              'Reply ONLY with JSON: {"ranking": [frame numbers from best to worst], "reason": "<one short sentence>"}')
    try:
        raw = await analyzer._chat(settings.vision_model, [{"role": "user", "content": prompt, "images": [_small_b64(p) for p in paths]}],
                                   json_mode=False, timeout=240)
        d = analyzer.json_in(raw)
        order = []
        for n in d.get("ranking", []):
            i = int(n) - 1
            if 0 <= i < len(paths) and i not in order:
                order.append(i)
        if not order:
            return None
        return order + [i for i in range(len(paths)) if i not in order], str(d.get("reason", "")).strip()
    except (AnalyzerError, ValueError, TypeError, json.JSONDecodeError):
        return None


async def write_headlines(description: str, title: str, lang: str, hint: str) -> list[str]:
    """Up to 4 short headlines (4 words or fewer) taken only from what the video shows."""
    prompt = f"""You write very short thumbnail headlines for a government communications team.
Video description: {description}
{('Video title: ' + title) if title else ''}
{('User context: ' + hint) if hint else ''}
Return ONLY JSON: {{"headlines": ["<3 different headlines: {HEADLINE_LANG.get(lang, 'English')}>"]}}
Each headline: 4 words or fewer, at most 28 characters, no full stop, not all capitals, no clickbait.
Only use what the description says. Do not invent facts, names, numbers or dates."""
    try:
        raw = await analyzer._chat(settings.text_model, [{"role": "user", "content": prompt}], json_mode=True, timeout=120)
        items = json.loads(raw).get("headlines", [])
    except (AnalyzerError, ValueError, TypeError, json.JSONDecodeError):
        return []
    out: list[str] = []
    for h in items:
        h = str(h).strip().strip('"').rstrip(".")[:40]
        if h and h not in out:
            out.append(h)
    return out[:4]
