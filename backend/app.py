"""Thin aggregator: wire routers, create tables, health checks, JSON logs."""
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import models  # noqa: F401  (register tables)
from db import Base, engine
import yt_thumbnail
from routes import accounts, analyze, facebook, li_manager, meta_manager, linkedin, posts, x_manager, xposts, thumbnails, yt_channels, yt_manager, yt_studio, youtube


class JsonFormatter(logging.Formatter):
    def format(self, r):
        return json.dumps({"ts": self.formatTime(r), "level": r.levelname, "logger": r.name, "msg": r.getMessage()})


h = logging.StreamHandler()
h.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[h])
logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx logs full URLs, and Meta and Threads tokens ride in the query string


@asynccontextmanager
async def lifespan(_):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        cols = [r[1] for r in (await conn.exec_driver_sql("PRAGMA table_info(publication)")).fetchall()]
        if "title" not in cols:  # POC-only migration for databases created before titles existed
            await conn.exec_driver_sql("ALTER TABLE publication ADD COLUMN title VARCHAR(120) DEFAULT ''")
        if "visibility" not in cols:
            await conn.exec_driver_sql("ALTER TABLE publication ADD COLUMN visibility VARCHAR(20) DEFAULT ''")
    yt_thumbnail.resume()
    yield


app = FastAPI(title="DGM Publishing POC", lifespan=lifespan)
app.include_router(accounts.router)
app.include_router(posts.router)
app.include_router(analyze.router)
app.include_router(facebook.router)
app.include_router(meta_manager.router)
app.include_router(youtube.router)
app.include_router(thumbnails.router)
app.include_router(yt_studio.router)
app.include_router(yt_manager.router)
app.include_router(yt_channels.router)
app.include_router(linkedin.router)
app.include_router(li_manager.router)
app.include_router(xposts.router)
app.include_router(x_manager.router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz():
    from config import settings
    return {"ok": bool(settings.zernio_api_key)}
