"""Channel profiles and a suggestion of which signed-in channels fit a video. Read-only."""
import asyncio
import re
import time

from fastapi import APIRouter
from pydantic import BaseModel

import analyzer
import yt_accounts
import yt_studio
import youtube
from ai_signals import KIDS_TERMS
from config import settings

router = APIRouter(prefix="/api/youtube/channels")
CACHE_S = 300
_cache: dict[str, tuple[float, dict]] = {}
STOP = set("the and for with that this from have your you are was were has not but all any can our out one into video videos about more".split())


class Suggest(BaseModel):
    description: str = ""
    title: str = ""
    kids: bool = False


def kidsish(p: dict) -> bool:
    """A channel that is for children: YouTube marks it so, or its own words say so."""
    return bool(p.get("made_for_kids")) or bool(KIDS_TERMS.search(" ".join([p.get("title", ""), p.get("handle", ""), p.get("description", ""), p.get("keywords", "")])))


async def _profile(key: str) -> dict | None:
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    yt_accounts.use(key)  # this task's own copy of the context
    try:
        ch = await yt_studio.channel()
    except youtube.YouTubeError:
        return None
    if not ch:
        return None
    acct = yt_accounts.current()
    p = {"key": key, "label": acct.label, "title": ch["title"], "handle": ch["handle"], "description": ch["description"], "keywords": ch["keywords"],
         "made_for_kids": ch["made_for_kids"], "verified": ch["long_uploads"] == "allowed", "subscribers": ch["subscribers"]}
    p["kids_channel"] = kidsish(p)
    _cache[key] = (time.time(), p)
    return p


async def _profiles(refresh: bool = False) -> list[dict]:
    if refresh:
        _cache.clear()
    keys = []
    for a in yt_accounts.load().values():
        yt_accounts.use(a.key)
        if youtube.connected():
            keys.append(a.key)
    return [p for p in await asyncio.gather(*(_profile(k) for k in keys)) if p]


@router.get("/profiles")
async def profiles(refresh: bool = False):
    return {"profiles": await _profiles(refresh)}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def _keyword_rank(ps: list[dict], body: Suggest) -> list[dict]:
    video = _words(f"{body.title} {body.description}")
    out = []
    for p in ps:
        shared = sorted(video & _words(f"{p['title']} {p['description']} {p['keywords']}"))
        out.append({"key": p["key"], "label": p["label"], "score": len(shared), "reason": f"shares the words {', '.join(shared[:4])}" if shared else "no shared topic found"})
    return sorted(out, key=lambda r: -r["score"])


async def _ai_rank(ps: list[dict], body: Suggest) -> list[dict] | None:
    lines = "\n".join(f"- key: {p['key']} | name: {p['title']} | about: {p['description'][:200] or 'not written'} | keywords: {p['keywords'][:120] or 'none'} | "
                      f"for kids: {'yes' if p['kids_channel'] else 'no'}" for p in ps)
    prompt = f"""You choose which YouTube channels should publish a video.
Video title: {body.title}
Video description: {body.description}
Audience: {'made for kids' if body.kids else 'general'}
Channels:
{lines}
Score every channel from 0 to 10 for how well the video fits its topic and audience. Use only the information above.
Return ONLY JSON: {{"picks": [{{"key": "<channel key>", "score": <0-10>, "reason": "<one short sentence>"}}]}}"""
    try:
        raw = await analyzer._chat(settings.text_model, [{"role": "user", "content": prompt}], json_mode=True, timeout=120)
        picks = analyzer.json_in(raw).get("picks", [])
    except (analyzer.AnalyzerError, ValueError, TypeError):
        return None
    by_key = {p["key"]: p for p in ps}
    out = [{"key": x["key"], "label": by_key[x["key"]]["label"], "score": float(x.get("score", 0)), "reason": str(x.get("reason", ""))[:140]}
           for x in picks if isinstance(x, dict) and x.get("key") in by_key]
    return sorted(out, key=lambda r: -r["score"]) if out else None


def _decide(ranked: list[dict], ps: list[dict], kids: bool, by: str) -> list[str]:
    """Which channels to tick. A kids video belongs on kids channels; any other video stays off them."""
    is_kids = {p["key"]: p["kids_channel"] for p in ps}
    good = 6 if by == "ai" else 2
    if kids:
        kids_keys = [p["key"] for p in ps if p["kids_channel"]]  # from the channels themselves, not from what the AI happened to score
        return kids_keys or [r["key"] for r in ranked if r["score"] >= good]
    return [r["key"] for r in ranked if not is_kids[r["key"]] and r["score"] >= good]


@router.post("/suggest")
async def suggest(body: Suggest):
    ps = await _profiles()
    if not ps:
        return {"recommended": [], "ranked": [], "by": "none"}
    if len(ps) == 1:
        return {"recommended": [ps[0]["key"]], "by": "only", "ranked": [{"key": ps[0]["key"], "label": ps[0]["label"], "score": 10, "reason": "your only signed-in channel"}]}
    ranked, by = await _ai_rank(ps, body), "ai"
    if not ranked:
        ranked, by = _keyword_rank(ps, body), "keywords"
    rec = _decide(ranked, ps, body.kids, by)
    for p in ps:  # a channel chosen by rule needs a reason on screen even if the AI did not score it
        if p["key"] in rec and not any(r["key"] == p["key"] for r in ranked):
            ranked.append({"key": p["key"], "label": p["label"], "score": 10, "reason": "a kids channel, and this video is made for kids"})
    return {"recommended": rec, "ranked": ranked, "by": by}
