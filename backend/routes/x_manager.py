"""Accounts manager for X: add an account with its X app's OAuth 2.0 Client ID and Secret, connect it, and see what is still missing."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import x_accounts
import xapi
from config import settings

router = APIRouter(prefix="/api/x/manager")
PORTAL = xapi.PORTAL
GUIDE = [
    {"title": "Create a project and an app", "do": "In the X Developer Console create a project, then an app inside it. X now charges per request (about $0.015 per post): add credits or auto-recharge under Billing.",
     "link": {"label": "Open the X Developer Console", "url": PORTAL}},
    {"title": "Set up user authentication", "do": "In the app press Set up under User authentication settings. App permissions: Read and write. Type of App: Web App, Automated App or Bot."},
    {"title": "Add the callback URL", "do": "In the same form, under Callback URI / Redirect URL, add the address shown on the right exactly as written (X does not accept localhost, so it uses 127.0.0.1). Website URL can be any address you own. Save."},
    {"title": "Copy the OAuth 2.0 keys", "do": "On Keys and tokens copy the OAuth 2.0 Client ID and Client Secret. The API Key, API Key Secret and the Access Token on that page are not needed here."},
    {"title": "Paste them here", "do": "Use Add account on this screen. The secret stays on this computer and is never shown again."},
    {"title": "Connect", "do": "Be signed in to the right X account in this browser, press Connect and authorize the app. The sign-in renews itself after that."},
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


def _card(a: x_accounts.Account) -> dict:
    """What the screen may see. The secret never leaves the server."""
    x_accounts.use(a.key)
    t = xapi.saved()
    return {"key": a.key, "label": a.label, "source": "file", "client_from": a.client_from, "configured": a.configured,
            "client_hint": (a.client_id[:8] + "...") if a.client_id else "", "has_secret": bool(a.client_secret),
            "connected": xapi.connected(), "expired": False, "name": t.get("name", ""), "email": f"@{t['username']}" if t.get("username") else ""}


def _get(key: str) -> x_accounts.Account:
    a = x_accounts.load().get(key)
    if not a:
        raise HTTPException(404, "That account does not exist.")
    return a


@router.get("/accounts")
async def list_accounts():
    return {"accounts": [_card(a) for a in x_accounts.load().values()], "redirect_uri": settings.x_redirect_uri, "js_origin": "", "guide": GUIDE}


@router.post("/accounts", status_code=201)
async def add_account(body: NewAccount):
    try:
        return _card(x_accounts.add(body.label, body.client_id, body.client_secret, body.client_from))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.patch("/accounts/{key}")
async def edit_account(key: str, body: EditAccount):
    _get(key)
    try:
        return _card(x_accounts.update(key, body.label, body.client_id, body.client_secret))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/accounts/{key}")
async def delete_account(key: str):
    _get(key)
    try:
        x_accounts.remove(key)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


def _item(id_: str, title: str, status: str, detail: str = "", action=None) -> dict:
    return {"id": id_, "title": title, "status": status, "detail": detail, "action": action}  # status: ok | todo | warn


@router.get("/accounts/{key}/check")
async def check(key: str):
    """A checklist for one account. X's sign-in page cannot be checked in advance, so the callback counts as done after the first good sign-in."""
    a = _get(key)
    x_accounts.use(key)
    items = [_item("client", "X app (OAuth 2.0 Client ID and Secret)", "ok" if a.configured else "todo",
                   "Saved." if a.configured else "Remove this account and add it again with the Client ID and Secret.")]
    if not a.configured:
        return {"key": key, "items": items}
    if not xapi.connected():
        items.append(_item("callback", "Callback URL in your X app", "todo",
                           f"Make sure {settings.x_redirect_uri} is listed exactly under Callback URI / Redirect URL, with App permissions Read and write. "
                           "X only shows a problem on its own page when you connect.",
                           [{"kind": "copy", "label": "Copy the callback URL", "value": settings.x_redirect_uri}, {"kind": "link", "label": "Open the X Developer Console", "url": PORTAL}]))
        items.append(_item("signin", "Signed in", "todo", "Press Connect (be signed in to the right X account in this browser) and authorize the app.",
                           {"kind": "connect", "label": f"Connect {a.label}", "opts": {}}))
        return {"key": key, "items": items}
    items.append(_item("callback", "Callback URL in your X app", "ok", "X accepted the sign-in."))
    try:
        me = await xapi.profile()
    except xapi.XError as e:
        items.append(_item("signin", "Sign-in still valid", "warn", e.message, {"kind": "connect", "label": "Connect again", "opts": {}}))
        return {"key": key, "items": items}
    items.append(_item("signin", "Signed in", "ok", f"{me['name']} @{me['username']}. The sign-in renews itself."))
    missing = [s for s in xapi.NEEDED if s not in me["granted"]]
    items.append(_item("post", "Permission to post videos", "todo" if missing else "ok",
                       f"This sign-in lacks {', '.join(missing)}. {xapi.SETTINGS_HINT} Then press Connect again." if missing else "Posting with video is allowed.",
                       {"kind": "connect", "label": "Connect again", "opts": {}} if missing else None))
    items.append(_item("credits", "X API credits", "warn", "X charges per request (about $0.015 per post) and this app cannot read your balance. If a post fails with no credits, add some in the X Developer Console.",
                       {"kind": "link", "label": "Open the X Developer Console", "url": PORTAL}))
    return {"key": key, "items": items}
