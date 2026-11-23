"""Accounts manager for LinkedIn: add an account with its LinkedIn app's client ID and secret, connect it, and see what is still missing."""
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import li_accounts
import linkedin
from config import settings

router = APIRouter(prefix="/api/linkedin/manager")
PORTAL = linkedin.PORTAL
GUIDE = [
    {"title": "Create a LinkedIn app", "do": "In the LinkedIn Developer portal press Create app. LinkedIn asks for a LinkedIn Page to attach the app to; pick or create a company page you manage.",
     "link": {"label": "Open the LinkedIn Developer portal", "url": PORTAL}},
    {"title": "Add the two products", "do": "On the app's Products tab, request Share on LinkedIn and Sign In with LinkedIn using OpenID Connect. Until you do, the Auth tab says No permissions added and nothing can sign in."},
    {"title": "Add the redirect URL, or skip it", "do": "For the Connect button: on the Auth tab, under Authorized redirect URLs for your app, add the redirect address shown on the right and press Update. "
     "To skip the redirect, use Connect with a token on the account's card with a token from the LinkedIn token generator.",
     "link": {"label": "Open the token generator", "url": linkedin.TOKEN_GENERATOR}},
    {"title": "Copy the client ID and secret", "do": "Still on the Auth tab, copy the Client ID and the Primary Client Secret."},
    {"title": "Paste them here", "do": "Use Add account on this screen. The secret stays on this computer and is never shown again."},
    {"title": "Connect", "do": "Press Connect (be signed in to the right LinkedIn account in this browser) or paste a token, and allow the app. A LinkedIn sign-in lasts 60 days; after that, connect again."},
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


def _card(a: li_accounts.Account) -> dict:
    """What the screen may see. The secret never leaves the server."""
    li_accounts.use(a.key)
    t = linkedin.saved()
    return {"key": a.key, "label": a.label, "source": "file", "client_from": a.client_from, "configured": a.configured,
            "client_hint": (a.client_id[:6] + "...") if a.client_id else "", "has_secret": bool(a.client_secret),
            "connected": linkedin.connected(), "expired": linkedin.expired(), "name": t.get("name", ""), "email": t.get("email", "")}


def _get(key: str) -> li_accounts.Account:
    a = li_accounts.load().get(key)
    if not a:
        raise HTTPException(404, "That account does not exist.")
    return a


@router.get("/accounts")
async def list_accounts():
    return {"accounts": [_card(a) for a in li_accounts.load().values()], "redirect_uri": settings.linkedin_redirect_uri,
            "js_origin": "", "guide": GUIDE}


@router.post("/accounts", status_code=201)
async def add_account(body: NewAccount):
    try:
        return _card(li_accounts.add(body.label, body.client_id, body.client_secret, body.client_from))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.patch("/accounts/{key}")
async def edit_account(key: str, body: EditAccount):
    _get(key)
    try:
        return _card(li_accounts.update(key, body.label, body.client_id, body.client_secret))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/accounts/{key}")
async def delete_account(key: str):
    _get(key)
    try:
        li_accounts.remove(key)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


def _item(id_: str, title: str, status: str, detail: str = "", action: dict | None = None) -> dict:
    return {"id": id_, "title": title, "status": status, "detail": detail, "action": action}  # status: ok | todo | warn


@router.get("/accounts/{key}/check")
async def check(key: str):
    """A checklist for one account: what works and what still needs doing. Reads only, changes nothing."""
    a = _get(key)
    li_accounts.use(key)
    items = [_item("client", "LinkedIn app (client ID and secret)", "ok" if a.configured else "todo",
                   "Saved." if a.configured else "Remove this account and add it again with the client ID and secret.")]
    if not a.configured:
        return {"key": key, "items": items}
    problem = await linkedin.check_setup()
    token_in = bool(problem) and linkedin.connected()  # signed in with a token: the redirect only matters for the Connect button
    items.append(_item("redirect", "LinkedIn accepts this app's sign-in", "ok" if token_in or not problem else "todo",
                       "Not set up, but you are signed in without it. It only matters if you want the Connect button to renew the sign-in." if token_in
                       else problem or f"Redirect address {settings.linkedin_redirect_uri} is accepted.",
                       [{"kind": "copy", "label": "Copy the redirect address", "value": settings.linkedin_redirect_uri},
                        {"kind": "link", "label": "Open the LinkedIn Developer portal", "url": PORTAL}] if problem and not token_in else None))
    if key in linkedin.scope_refused:
        items.append(_item("permissions", "Permissions in the LinkedIn app", "todo", linkedin.NO_PERMISSIONS, {"kind": "link", "label": "Open the LinkedIn Developer portal", "url": PORTAL}))
    if not linkedin.connected():
        gone = linkedin.expired()
        items.append(_item("signin", "Signed in", "warn" if gone else "todo",
                           "The 60-day LinkedIn sign-in has run out. Press Connect and allow the app again." if gone
                           else "Press Connect (be signed in to the right LinkedIn account in this browser), or use Connect with a token on this account's card.",
                           {"kind": "connect", "label": f"Connect {a.label}", "opts": {}}))
        return {"key": key, "items": items}
    try:
        me = await linkedin.profile()
    except linkedin.LinkedInError as e:
        items.append(_item("signin", "Sign-in still valid", "warn", e.message, {"kind": "connect", "label": "Connect again", "opts": {}}))
        return {"key": key, "items": items}
    left = linkedin.saved().get("expires_at", 0)
    days = max(0, int((left - time.time()) // 86400))
    how = " (with a pasted token)" if linkedin.saved().get("via") == "token" else ""
    items.append(_item("signin", "Signed in", "ok", f"{me['name']}{' - ' + me['email'] if me['email'] else ''}{how}. The sign-in has about {days} days left."))
    can = linkedin.POST_SCOPE in me["granted"]
    items.append(_item("post", "Permission to post", "ok" if can else "todo",
                       "Posting as this member is allowed." if can else f"This sign-in cannot post yet. {linkedin.APP_PRODUCTS} Then press Connect again.",
                       None if can else {"kind": "connect", "label": "Connect again", "opts": {}}))
    return {"key": key, "items": items}
