"""Probe a video and pull a few evenly spaced frames with ffmpeg (all local)."""
import asyncio
import base64
import json
import tempfile
from pathlib import Path


async def _run(*cmd: str) -> bytes:
    p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await p.communicate()
    if p.returncode:
        raise RuntimeError(err.decode()[-300:] or "ffmpeg failed")
    return out


async def probe(path: Path) -> dict:
    out = await _run("ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path))
    d = json.loads(out)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    return {"duration_s": round(float(d.get("format", {}).get("duration", 0)), 1), "width": w, "height": h,
            "orientation": "vertical" if h > w else "horizontal" if w > h else "square",
            "has_audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


async def extract_frames(path: Path, duration: float, count: int) -> list[str]:
    """Return base64 JPEGs taken at the middle of `count` equal slices of the video."""
    count = max(1, count)
    with tempfile.TemporaryDirectory() as tmp:
        shots = []
        for i in range(count):
            t = max(0.0, duration * (i + 0.5) / count)
            out = Path(tmp) / f"f{i}.jpg"
            await _run("ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                       "-vf", "scale='min(640,iw)':-2", "-q:v", "4", str(out))
            if out.exists():
                shots.append(base64.b64encode(out.read_bytes()).decode())
        return shots
