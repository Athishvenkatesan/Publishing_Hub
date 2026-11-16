"""Thin aggregator: wire routers, create tables, health checks, JSON logs."""
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import models  # noqa: F401  (register tables)
from db import Base, engine
from routes import accounts, analyze, posts


class JsonFormatter(logging.Formatter):
    def format(self, r):
        return json.dumps({"ts": self.formatTime(r), "level": r.levelname, "logger": r.name, "msg": r.getMessage()})


h = logging.StreamHandler()
h.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[h])


@asynccontextmanager
async def lifespan(_):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        cols = [r[1] for r in (await conn.exec_driver_sql("PRAGMA table_info(publication)")).fetchall()]
        if "title" not in cols:  # POC-only migration for databases created before titles existed
            await conn.exec_driver_sql("ALTER TABLE publication ADD COLUMN title VARCHAR(120) DEFAULT ''")
    yield


app = FastAPI(title="DGM Publishing POC", lifespan=lifespan)
app.include_router(accounts.router)
app.include_router(posts.router)
app.include_router(analyze.router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz():
    from config import settings
    return {"ok": bool(settings.zernio_api_key)}
