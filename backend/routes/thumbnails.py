"""Thumbnails for the YouTube screen: candidate frames ranked by the local model, headline ideas, and re-rendering on demand."""
import asyncio
import base64
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

import frames
import thumb_ai
import thumb_frames
import thumb_jobs
import thumb_render
from config import settings
from routes.posts import ALLOWED, CHUNK

router = APIRouter(prefix="/api/thumbnails")


async def _save(file: UploadFile) -> Path:
    size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "v.mp4").suffix) as tmp:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > settings.max_video_mb * 1024 * 1024:
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(422, f"Video is over {settings.max_video_mb} MB")
            tmp.write(chunk)
    return Path(tmp.name)


async def _frames(path: Path) -> tuple[dict, str, list[dict]]:
    meta = await frames.probe(path)
    job, folder = thumb_jobs.new_job()
    found = await thumb_frames.extract(path, meta["duration_s"], folder)
    if not found:
        raise HTTPException(422, "Could not read frames from this video")
    return meta, job, found


@router.post("/candidates")
async def candidates(file: UploadFile = File(...), lang: str = Form("en"), hint: str = Form(""),
                     description: str = Form(""), title: str = Form("")):
    """Three thumbnail options from one video. Works without the AI: then they are ordered by sharpness and have no headline."""
    if Path(file.filename or "").suffix.lower() not in ALLOWED:
        raise HTTPException(422, "Video must be .mp4 or .mov")
    path = await _save(file)
    try:
        meta, job, found = await _frames(path)
    except RuntimeError as e:
        raise HTTPException(422, f"Could not read this video: {e}")
    finally:
        path.unlink(missing_ok=True)
    ranked_by, note = "sharpness", ""
    ai = await thumb_ai.rank_frames([f["path"] for f in found])
    if ai:
        order, note = ai
        found, ranked_by = [found[i] for i in order], "ai"
    top = found[:3]
    headlines = await thumb_ai.write_headlines(description, title, lang, hint) if description else []
    style = "band" if headlines else "none"
    jpgs = await asyncio.gather(*(asyncio.to_thread(thumb_render.render, f["path"], headlines[0] if headlines else "", style, False) for f in top))
    return {"job_id": job, "orientation": meta["orientation"], "ranked_by": ranked_by, "note": note, "headlines": headlines, "style": style,
            "candidates": [{"id": f["id"], "t": f["t"], "image": "data:image/jpeg;base64," + base64.b64encode(j).decode()} for f, j in zip(top, jpgs)]}


class RenderIn(BaseModel):
    job_id: str
    frame_id: str
    headline: str = ""
    style: str = "band"
    logo: bool = False


@router.post("/render")
async def render(body: RenderIn):
    path = thumb_jobs.frame_path(body.job_id, body.frame_id)
    if path is None:
        raise HTTPException(410, "This thumbnail session expired. Press Regenerate.")
    if body.style not in thumb_render.STYLES or len(body.headline) > 80:
        raise HTTPException(422, "Unknown style or headline over 80 characters")
    jpg = await asyncio.to_thread(thumb_render.render, path, body.headline, body.style, body.logo)
    return Response(content=jpg, media_type="image/jpeg")
