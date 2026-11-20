"""Accounts manager for YouTube: add an account with its Google client ID and secret, connect it, and see what is still missing."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import yt_accounts
import yt_studio
import youtube
from config import settings

router = APIRouter(prefix="/api/youtube/manager")
CONSOLE = "https://console.cloud.google.com"
GUIDE = [
    {"title": "Create a Google Cloud project", "do": "Open Google Cloud, create a project (or pick one), and keep it selected.", "link": {"label": "Open Google Cloud", "url": CONSOLE}},
    {"title": "Turn on the YouTube Data API", "do": "APIs & Services, Library, search YouTube Data API v3, Enable. For reports also enable YouTube Analytics API.",
     "link": {"label": "Open the API library", "url": f"{CONSOLE}/apis/library/youtube.googleapis.com"}},
    {"title": "Set up the consent screen", "do": "Google Auth Platform, Audience: choose External. Under Test users, add the Google account that owns the channel.",
     "link": {"label": "Open the consent screen", "url": f"{CONSOLE}/auth/audience"}},
    {"title": "Create the OAuth client", "do": "Credentials, Create credentials, OAuth client ID. Choose Desktop app (needs no redirect address). "
     "If you choose Web application, add the redirect address shown below under Authorized redirect URIs (not under JavaScript origins). The web page address also works as a redirect address.", "link": {"label": "Open Credentials", "url": f"{CONSOLE}/apis/credentials"}},
    {"title": "Paste the client ID and secret here", "do": "Use Add account on this screen. The secret stays on this computer and is never shown again."},
    {"title": "Connect and verify", "do": "Press Connect, sign in as the channel owner and allow access. Then verify the channel by phone so custom thumbnails work.",
     "link": {"label": "Verify a channel", "url": youtube.VERIFY_URL}},
]


class NewAccount(BaseModel):
    label: str
    client_id: str = ""
    client_secret: str = ""
    client_from: str = ""


class EditAccount(BaseModel):
    label: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


def _card(a: yt_accounts.Account) -> dict:
    """What the screen may see. The secret never leaves the server."""
    yt_accounts.use(a.key)
    return {"key": a.key, "label": a.label, "source": a.source, "client_from": a.client_from, "configured": a.configured,
            "client_hint": (a.client_id[:12] + "...") if a.client_id else "", "has_secret": bool(a.client_secret),
            "connected": youtube.connected(), "env_names": a.env_names if a.source == "env" else ""}


def _get(key: str) -> yt_accounts.Account:
    a = yt_accounts.load().get(key)
    if not a:
        raise HTTPException(404, "That account does not exist.")
    return a


@router.get("/accounts")
async def list_accounts():
    return {"accounts": [_card(a) for a in yt_accounts.load().values()], "redirect_uri": settings.youtube_redirect_uri,
            "js_origin": settings.frontend_url, "guide": GUIDE}


@router.post("/accounts", status_code=201)
async def add_account(body: NewAccount):
    try:
        return _card(yt_accounts.add(body.label, body.client_id, body.client_secret, body.client_from))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.patch("/accounts/{key}")
async def edit_account(key: str, body: EditAccount):
    _get(key)
    try:
        return _card(yt_accounts.update(key, body.label, body.client_id, body.client_secret))
    except PermissionError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/accounts/{key}")
async def delete_account(key: str):
    _get(key)
    try:
        yt_accounts.remove(key)
    except PermissionError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


def _item(id_: str, title: str, status: str, detail: str = "", action: dict | None = None) -> dict:
    return {"id": id_, "title": title, "status": status, "detail": detail, "action": action}  # status: ok | todo | warn


async def _channel_items(granted: set[str]) -> list[dict]:
    items: list[dict] = []
    try:
        ch = await youtube.channel()
    except youtube.YouTubeError as e:
        return [_item("channel", "Channel reachable", "warn", e.message, {"kind": "connect", "label": "Connect again", "opts": {}})]
    if not ch:
        return [_item("channel", "Channel found", "warn", "This Google account has no YouTube channel yet. Create one on YouTube, then check again.")]
    items.append(_item("channel", "Channel found", "ok", f"{ch['title']} {ch['handle']}".strip()))
    ver = ch.get("verified")
    items.append(_item("verified", "Channel verified by phone", "ok" if ver else "todo" if ver is False else "warn",
                       "Custom thumbnails and videos over 15 minutes are unlocked." if ver else "YouTube blocks custom thumbnails and long videos until the channel is verified.",
                       None if ver else {"kind": "link", "label": "Verify on YouTube", "url": ch.get("verify_url") or youtube.VERIFY_URL}))
    items.append(_item("manage", "Permission to edit and delete videos", "ok" if youtube.MANAGE_SCOPE in granted else "todo",
                       "Needed for editing, changing visibility, rescheduling and deleting." if youtube.MANAGE_SCOPE not in granted else "Granted.",
                       None if youtube.MANAGE_SCOPE in granted else {"kind": "connect", "label": "Add this permission", "opts": {"manage": True}}))
    if youtube.ANALYTICS_SCOPE not in granted:
        items.append(_item("reports", "Permission to read reports", "todo", "Needed for the Reports tab in Studio management.",
                           {"kind": "connect", "label": "Add this permission", "opts": {"reports": True}}))
        return items
    from datetime import date, timedelta
    try:
        await yt_studio.report(date.today() - timedelta(days=8), date.today() - timedelta(days=1), "views")
        items.append(_item("reports", "Reports available", "ok", "Permission granted and the YouTube Analytics API is on."))
    except yt_studio.ReportsUnavailable as e:
        items.append(_item("reports", "YouTube Analytics API", "todo", e.message, {"kind": "link", "label": "Turn it on", "url": f"{CONSOLE}/apis/library/youtubeanalytics.googleapis.com"}
                           if e.code == "api_disabled" else {"kind": "connect", "label": "Add this permission", "opts": {"reports": True}}))
    except youtube.YouTubeError as e:
        items.append(_item("reports", "Reports", "warn", e.message))
    return items


@router.get("/accounts/{key}/check")
async def check(key: str):
    """A checklist for one account: what works and what still needs doing. Reads only, changes nothing."""
    a = _get(key)
    yt_accounts.use(key)
    items = [_item("client", "Google app (client ID and secret)", "ok" if a.configured else "todo",
                   "Saved." if a.configured else (f"Add {a.env_names} in backend/.env." if a.source == "env" else "Edit this account and paste both values."))]
    if not a.configured:
        return {"key": key, "items": items}
    problem = await youtube.check_setup()
    items.append(_item("redirect", "Google accepts this app's sign-in", "todo" if problem else "ok",
                       problem or f"Redirect address {settings.youtube_redirect_uri} is accepted.",
                       {"kind": "copy", "label": "Copy the redirect address", "value": settings.youtube_redirect_uri} if problem else None))
    if not youtube.connected():
        items.append(_item("signin", "Signed in", "todo", "Press Connect and sign in as the channel owner.", {"kind": "connect", "label": f"Connect {a.label}", "opts": {}}))
        return {"key": key, "items": items}
    items.append(_item("signin", "Signed in", "ok", "A saved sign-in exists for this account."))
    try:
        granted = set(await yt_studio.scopes())
    except youtube.YouTubeError as e:
        items.append(_item("signin", "Sign-in still valid", "warn", e.message, {"kind": "connect", "label": "Connect again", "opts": {}}))
        return {"key": key, "items": items}
    return {"key": key, "items": items + await _channel_items(granted)}
