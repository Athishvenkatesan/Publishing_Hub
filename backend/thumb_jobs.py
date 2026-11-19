"""Short-lived working folders for thumbnail candidates, so a headline edit can re-render without re-reading the video."""
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(tempfile.gettempdir()) / "dgm-thumbs"
TTL_S = 3600
_JOB, _FRAME = re.compile(r"^[a-f0-9]{12}$"), re.compile(r"^f\d{1,2}$")


def cleanup() -> None:
    if ROOT.exists():
        for d in ROOT.iterdir():
            if time.time() - d.stat().st_mtime > TTL_S:
                shutil.rmtree(d, ignore_errors=True)


def new_job() -> tuple[str, Path]:
    cleanup()
    job = uuid.uuid4().hex[:12]
    folder = ROOT / job
    folder.mkdir(parents=True)
    return job, folder


def frame_path(job: str, frame: str) -> Path | None:
    """The saved frame, or None when the ids are malformed (no path tricks) or the job has expired."""
    if not (_JOB.match(job) and _FRAME.match(frame)):
        return None
    p = ROOT / job / f"{frame}.jpg"
    return p if p.exists() else None
