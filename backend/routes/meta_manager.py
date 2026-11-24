"""Accounts manager for Meta: the Facebook + Instagram token and the Threads token. See each one, replace it, make it last 60 days,
and set your own expiry date. Secrets never leave the server; tokens are shown only as their first characters."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import expiry_dates
import meta
import meta_tokens as mt

router = APIRouter(prefix="/api/meta/manager")
DEV = "https://developers.facebook.com/apps"
EXPLORER = "https://developers.facebook.com/tools/explorer"
GUIDE = [
    {"title": "Open your Meta app", "do": "In Meta for Developers open the app that posts (Use cases: Manage everything on your Page, Instagram API, Threads API).", "link": {"label": "Open Meta for Developers", "url": DEV}},
    {"title": "Make the Facebook + Instagram token", "do": "In the Graph API Explorer pick the app and add pages_show_list, pages_read_engagement, pages_manage_posts, "
     "instagram_basic and instagram_content_publish. Press Generate Access Token, allow your Page and Instagram account, and copy the token.", "link": {"label": "Open the Graph API Explorer", "url": EXPLORER}},
    {"title": "Make it last 60 days", "do": "Explorer tokens last 1 to 2 hours. Paste the App ID and App secret (App settings, Basic) in Edit once, and every token you paste is swapped for a 60-day one."},
    {"title": "Link Instagram to the Page", "do": "Instagram must be a professional account linked to your Facebook Page (Meta Business Suite, Settings, Instagram accounts)."},
    {"title": "Make the Threads token", "do": "Threads has its own token. Add your Threads account as a Threads Tester (App roles), accept the invite in the Threads app, "
     "then generate a token with threads_basic and threads_content_publish. Add the Threads app secret to make it last 60 days."},
]


class EditToken(BaseModel):
    token: str | None = None        # a new token to use ("" removes it)
    app_id: str | None = None       # Meta only
    app_secret: str | None = None   # Meta app secret, or the Threads app secret
    expires_on: str | None = None   # your own reminder date, YYYY-MM-DD; "" clears it


def _hint(token: str) -> str:
    return f"{token[:8]}..." if token else ""


async def _meta_card() -> dict:
    v, token = mt.env(), mt.env().get("META_ACCESS_TOKEN", "")
    card = {"key": "meta", "label": "Facebook + Instagram", "has_token": bool(token), "token_hint": _hint(token), "valid": False, "error": "",
            "who": "", "expires_at": None, "never_expires": False, "app_id": v.get("META_APP_ID", ""), "has_app_secret": bool(v.get("META_APP_SECRET")),
            "scopes": [], "pages": [], "can": {}, **expiry_dates.info("meta", "meta")}
    if not token:
        return card
    d = await mt.meta_debug(token)
    card.update(valid=d["is_valid"], error=d.get("error", ""), scopes=d.get("scopes", []), app_id=card["app_id"] or d.get("app_id", ""),
                expires_at=d.get("expires_at") or None, never_expires=d["is_valid"] and not d.get("expires_at"))
    if d["is_valid"]:
        try:
            c = await meta.check()
            card.update(who=c["user"]["name"], can={x["key"]: x["ok"] for x in c["capabilities"]},
                        pages=[{"name": p["name"].strip(), "instagram": (p.get("instagram") or {}).get("username", "")} for p in c["pages"]])
        except meta.MetaError as e:
            card["error"] = e.message
    return card


async def _threads_card() -> dict:
    v, token = mt.env(), mt.env().get("THREADS_ACCESS_TOKEN", "")
    until = int(v.get("THREADS_TOKEN_EXPIRES") or 0) or None
    card = {"key": "threads", "label": "Threads", "has_token": bool(token), "token_hint": _hint(token), "valid": False, "error": "", "who": "",
            "expires_at": until, "never_expires": False, "has_app_secret": bool(v.get("THREADS_APP_SECRET")), **expiry_dates.info("meta", "threads")}
    if token:
        me = await mt.threads_me(token)
        card.update(valid=me["ok"], who=f"@{me['username']}" if me.get("username") else "", error=me.get("error", ""))
    return card


async def _card(key: str) -> dict:
    return await (_meta_card() if key == "meta" else _threads_card())


def _key(key: str) -> str:
    if key not in ("meta", "threads"):
        raise HTTPException(404, "That account does not exist.")
    return key


@router.get("/accounts")
async def accounts():
    return {"accounts": [await _meta_card(), await _threads_card()], "guide": GUIDE}


async def _new_token(key: str, token: str, v: dict) -> dict[str, str]:
    """The .env lines for a pasted token: swapped for a 60-day one when the app secret is known."""
    if key == "meta":
        app_id = v.get("META_APP_ID") or (await mt.meta_debug(token)).get("app_id", "")
        if app_id and v.get("META_APP_SECRET"):
            token, _ = await mt.meta_long(token, app_id, v["META_APP_SECRET"])
        return {"META_ACCESS_TOKEN": token, **({"META_APP_ID": app_id} if app_id and not v.get("META_APP_ID") else {})}
    if v.get("THREADS_APP_SECRET"):
        token, until = await mt.threads_long(token, v["THREADS_APP_SECRET"])
        return {"THREADS_ACCESS_TOKEN": token, "THREADS_TOKEN_EXPIRES": str(until)}
    return {"THREADS_ACCESS_TOKEN": token, "THREADS_TOKEN_EXPIRES": ""}  # unknown: a tester-tool token lasts about 1 hour


@router.get("/accounts/{key}/values")
async def edit_values(key: str):
    """Everything the Edit panel shows, tokens and secrets included. Only read when Edit opens, never in the list."""
    v = mt.env()
    if _key(key) == "meta":
        app_id = v.get("META_APP_ID") or ((await mt.meta_debug(v["META_ACCESS_TOKEN"])).get("app_id", "") if v.get("META_ACCESS_TOKEN") else "")
        return {"token": v.get("META_ACCESS_TOKEN", ""), "app_id": app_id, "app_secret": v.get("META_APP_SECRET", ""),
                "expires_on": expiry_dates.get("meta", key)}
    return {"token": v.get("THREADS_ACCESS_TOKEN", ""), "app_secret": v.get("THREADS_APP_SECRET", ""), "expires_on": expiry_dates.get("meta", key)}


@router.patch("/accounts/{key}")
async def edit(key: str, body: EditToken):
    _key(key)
    try:
        when = expiry_dates.clean(body.expires_on) if body.expires_on is not None else None
        values: dict[str, str] = {}
        if key == "meta" and body.app_id is not None:
            if body.app_id.strip() and not body.app_id.strip().isdigit():
                raise ValueError("The App ID is a number, like 1145493691227848.")
            values["META_APP_ID"] = body.app_id.strip()
        if body.app_secret is not None:  # "" removes it
            values["META_APP_SECRET" if key == "meta" else "THREADS_APP_SECRET"] = body.app_secret.strip()
        if values:
            mt.save(values)
        if body.token is not None:
            token = body.token.strip()
            if token and (len(token) < 20 or " " in token):
                raise ValueError("That does not look like a token. Copy the whole token and paste it again.")
            mt.save(await _new_token(key, token, mt.env()) if token else ({"META_ACCESS_TOKEN": ""} if key == "meta" else {"THREADS_ACCESS_TOKEN": "", "THREADS_TOKEN_EXPIRES": ""}))
        if when is not None:
            expiry_dates.put("meta", key, when)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except meta.MetaError as e:
        raise HTTPException(e.status, e.message)
    return await _card(key)


@router.post("/accounts/{key}/extend")
async def extend(key: str):
    """Swap the saved token for a 60-day one (needs the app secret)."""
    _key(key)
    v = mt.env()
    token = v.get("META_ACCESS_TOKEN" if key == "meta" else "THREADS_ACCESS_TOKEN", "")
    if not token:
        raise HTTPException(422, "There is no token to extend. Paste one with Edit first.")
    if not v.get("META_APP_SECRET" if key == "meta" else "THREADS_APP_SECRET"):
        raise HTTPException(422, "Add the app secret with Edit first. It is what lets this app make a 60-day token.")
    try:
        mt.save(await _new_token(key, token, v))
    except meta.MetaError as e:
        raise HTTPException(e.status, e.message)
    return await _card(key)
