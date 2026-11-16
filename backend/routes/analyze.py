"""POST /api/analyze: video in, suggested title/caption/hashtags out. Local only."""
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

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


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), lang: str = Form("en"), hint: str = Form("")):
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
            description = await analyzer.describe(shots, meta, hint)
            copy = await analyzer.write_copy(description, meta, lang, hint)
        except analyzer.AnalyzerError as e:
            raise HTTPException(503, str(e))
        except RuntimeError as e:
            raise HTTPException(422, f"Could not read this video: {e}")
    return {"meta": meta, "description": description, "copy": copy}
