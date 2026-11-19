"""Thumbnail candidates: evenly spaced full-size frames, the dark ones dropped, then the sharpest, spread apart in time."""
import asyncio
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

from frames import _run


def _score(path: Path) -> tuple[float, float]:
    """(brightness, sharpness) on a small grayscale copy. Sharpness = variance of the edge image."""
    with Image.open(path) as im:
        g = im.convert("L")
        g.thumbnail((320, 320))
        return ImageStat.Stat(g).mean[0], ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).var[0]


async def extract(path: Path, duration: float, out_dir: Path, count: int = 12, keep: int = 6) -> list[dict]:
    """Up to `keep` frames: [{"id","t","path","sharp"}], best first. Frames are saved in out_dir at up to 1920 px wide."""
    found = []
    for i in range(count):
        t = max(0.0, duration * (0.08 + 0.84 * (i / (count - 1) if count > 1 else 0.5)))  # skip the very start and end
        out = out_dir / f"f{i}.jpg"
        try:
            await _run("ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                       "-vf", "scale='min(1920,iw)':-2", "-q:v", "3", str(out))
        except RuntimeError:
            continue
        if out.exists():
            mean, sharp = await asyncio.to_thread(_score, out)
            found.append({"id": f"f{i}", "t": round(t, 1), "path": out, "mean": mean, "sharp": sharp})
    usable = [f for f in found if 22 <= f["mean"] <= 240] or found  # drop near-black and blown-out frames
    usable.sort(key=lambda f: f["sharp"], reverse=True)
    chosen: list[dict] = []
    gap = 0.05 * duration
    for f in usable:  # greedy: sharpest first, but not two frames from almost the same moment
        if all(abs(f["t"] - c["t"]) >= gap for c in chosen):
            chosen.append(f)
    for f in usable:  # very short clips: top up so we always have something to show
        if len(chosen) >= keep:
            break
        if f not in chosen:
            chosen.append(f)
    return chosen[:keep]
