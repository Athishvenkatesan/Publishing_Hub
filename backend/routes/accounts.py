"""Accounts: list, connect (OAuth link) and disconnect - all inside our app."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import zernio

router = APIRouter(prefix="/api")
PLATFORMS = ["instagram", "youtube", "tiktok", "facebook", "linkedin", "twitter"]


class ConnectIn(BaseModel):
    platform: str
    return_to: str


def _fail(e: zernio.ZernioError):
    raise HTTPException(e.status, e.message)


@router.get("/accounts")
async def accounts():
    try:
        return {"accounts": await zernio.list_accounts(), "platforms": PLATFORMS}
    except zernio.ZernioError as e:
        _fail(e)


@router.post("/accounts/connect")
async def connect(body: ConnectIn):
    if body.platform not in PLATFORMS:
        raise HTTPException(422, "Unsupported platform.")
    try:
        return {"url": await zernio.connect_url(body.platform, body.return_to)}
    except zernio.ZernioError as e:
        _fail(e)


@router.delete("/accounts/{account_id}")
async def disconnect(account_id: str):
    try:
        await zernio.disconnect_account(account_id)
        return {"ok": True}
    except zernio.ZernioError as e:
        _fail(e)
