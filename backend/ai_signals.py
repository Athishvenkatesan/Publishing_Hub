"""Signals that a video was made or changed with AI, and whether it is aimed at children.
Conservative on purpose: a signal is a reason to tick YouTube's disclosure box, never proof, and finding no signal
does not prove a video is not AI. The user always has the last word."""
import json
import re
from pathlib import Path

from frames import _run

HEAD_TAIL = 8 * 1024 * 1024  # AI tools write their labels near the start or end of the file
BYTE_MARKERS = {
    b"trainedAlgorithmicMedia": "the file's own metadata says it was made by an AI model",
    b"compositeWithTrainedAlgorithmicMedia": "the file's own metadata says AI was used in part of it",
    b"urn:c2pa": "the file carries Content Credentials (C2PA), which AI tools such as Sora add",
}
TOOLS = ["sora", "veo", "runway", "pika", "kling", "luma", "dream machine", "hailuo", "minimax", "pixverse", "vidu", "hunyuan", "seedance",
         "stable video", "midjourney", "firefly", "synthesia", "heygen", "d-id", "higgsfield", "genmo", "haiper", "invideo", "pollo"]
TOOL_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in TOOLS) + r")\b", re.I)
AI_HINT = re.compile(r"\b(ai[- ]generated|made (?:with|by) ai|generated (?:with|by) ai|ai video|ai[- ]made|text[- ]to[- ]video)\b|\b(sora|veo|runway|midjourney|kling|pika)\b", re.I)
KIDS_HINT = re.compile(r"\b(kids?|children|child|toddlers?|nursery|preschool|baby|babies)\b", re.I)
KIDS_TERMS = KIDS_HINT


async def file_markers(path: Path) -> list[str]:
    """What the file itself says: standard AI labels in the bytes, and AI tool names in its tags."""
    found: list[str] = []
    try:
        with open(path, "rb") as f:
            head = f.read(HEAD_TAIL)
            f.seek(0, 2)
            size = f.tell()
            tail = b""
            if size > HEAD_TAIL:
                f.seek(max(HEAD_TAIL, size - HEAD_TAIL))
                tail = f.read()
        blob = head + tail
        found += [why for needle, why in BYTE_MARKERS.items() if needle in blob]
    except OSError:
        pass
    try:
        out = await _run("ffprobe", "-v", "error", "-print_format", "json", "-show_entries", "format_tags:stream_tags", str(path))
        d = json.loads(out)
        tags = list((d.get("format", {}).get("tags") or {}).values())
        for s in d.get("streams", []):
            tags += list((s.get("tags") or {}).values())
        m = TOOL_RE.search(" ".join(str(t) for t in tags))
        if m:
            found.append(f"the file's tags mention an AI video tool ({m.group(1)})")
    except (RuntimeError, ValueError):
        pass
    return found


def video_signals(markers: list[str], looks: dict | None, hint: str) -> dict:
    """The two suggested settings, each with the reason shown to the user. looks = the vision model's answer, or None."""
    ai_why = list(markers)
    if hint and AI_HINT.search(hint):
        ai_why.append("your context note says it is AI-made")
    if looks and looks.get("ai_generated") and looks.get("ai_confidence") in ("high", "medium"):
        ai_why.append(f"the AI model thinks it looks AI-generated{': ' + looks['ai_reason'] if looks.get('ai_reason') else ''}")
    kids_why = []
    if hint and KIDS_HINT.search(hint):
        kids_why.append("your context note mentions children")
    if looks and looks.get("for_kids") and looks.get("kids_confidence") in ("high", "medium"):
        kids_why.append(f"the AI model thinks it is made for children{': ' + looks['kids_reason'] if looks.get('kids_reason') else ''}")
    return {
        "ai_generated": {"value": bool(ai_why), "reason": "Ticked because " + "; ".join(ai_why) + "." if ai_why
                         else "No sign of AI was found in the file or the picture. If you used AI tools, tick it yourself."},
        "made_for_kids": {"value": bool(kids_why), "reason": "Ticked because " + "; ".join(kids_why) + "." if kids_why
                          else "It looks aimed at a general audience. If children are the audience, tick it yourself."},
    }
