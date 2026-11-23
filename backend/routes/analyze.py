"""POST /api/analyze: video in, suggested title/caption/hashtags out. Local only."""
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

import ai_signals
import analyzer
import frames
from config import settings

router = APIRouter(prefix="/api")


@router.get("/analyze/status")
async def status():
    """Tell the screen whether the local models are ready, before the user waits for nothing."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            tags = (await c.get(f"{settings.ollama_url}/api/tags")).json().get("models", [])
    except Exception:
        return {"ready": False, "reason": "Local model server (Ollama) is not running."}
    have = {m["name"] for m in tags}
    missing = [m for m in (settings.vision_model, settings.text_model) if m not in have]
    return {"ready": not missing, "reason": f"Missing model: {', '.join(missing)}" if missing else "",
            "vision_model": settings.vision_model, "text_model": settings.text_model}


async def _watch(file: UploadFile, hint: str) -> tuple[dict, str, list[str], list[str]]:
    """Read the clip, look at frames, ask the vision model what it shows. Returns (meta, description, frames, file markers)."""
    suffix = Path(file.filename or "v.mp4").suffix.lower()
    if suffix not in (".mp4", ".mov"):
        raise HTTPException(422, "Video must be .mp4 or .mov")
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        tmp.flush()
        try:
            meta = await frames.probe(Path(tmp.name))
            shots = await frames.extract_frames(Path(tmp.name), meta["duration_s"], settings.analyze_frames)
            if not shots:
                raise HTTPException(422, "Could not read frames from this video")
            return meta, await analyzer.describe(shots, meta, hint), shots, await ai_signals.file_markers(Path(tmp.name))
        except analyzer.AnalyzerError as e:
            raise HTTPException(503, str(e))
        except RuntimeError as e:
            raise HTTPException(422, f"Could not read this video: {e}")


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), lang: str = Form("en"), hint: str = Form("")):
    meta, description, *_ = await _watch(file, hint)
    try:
        return {"meta": meta, "description": description, "copy": await analyzer.write_copy(description, meta, lang, hint)}
    except analyzer.AnalyzerError as e:
        raise HTTPException(503, str(e))


@router.post("/analyze/youtube")
async def analyze_youtube(file: UploadFile = File(...), lang: str = Form("en"), hint: str = Form("")):
    """Same watch step, then the fuller YouTube package (title options, description, tags, category, thumbnail ideas)."""
    meta, description, shots, markers = await _watch(file, hint)
    try:
        looks = await analyzer.classify(shots, meta, hint)  # vision model is still loaded, so this is quick
        pkg = await analyzer.write_youtube(description, meta, lang, hint)
        return {"meta": meta, "description": description, "youtube": {**pkg, "suggestions": ai_signals.video_signals(markers, looks, hint)}}
    except analyzer.AnalyzerError as e:
        raise HTTPException(503, str(e))


@router.post("/analyze/linkedin")
async def analyze_linkedin(file: UploadFile = File(...), lang: str = Form("en"), hint: str = Form("")):
    """Same watch step, then a LinkedIn post: opening-line options, the text with hashtags, and a video title."""
    meta, description, *_ = await _watch(file, hint)
    try:
        return {"meta": meta, "description": description, "linkedin": await analyzer.write_linkedin(description, meta, lang, hint)}
    except analyzer.AnalyzerError as e:
        raise HTTPException(503, str(e))


@router.post("/analyze/x")
async def analyze_x(file: UploadFile = File(...), lang: str = Form("en"), hint: str = Form("")):
    """Same watch step, then three short posts for X."""
    meta, description, *_ = await _watch(file, hint)
    try:
        return {"meta": meta, "description": description, "x": await analyzer.write_x(description, meta, lang, hint)}
    except analyzer.AnalyzerError as e:
        raise HTTPException(503, str(e))
