"""The Meta and Threads tokens behind the Meta screen: what each one is, when it runs out, and swapping a short token
(1-2 hours, from the Graph API Explorer or the Threads tester tool) for a long one (about 60 days) with the app secret.
Everything is saved in backend/.env, so the rest of the app picks it up straight away."""
import time

import httpx

import envfile
import meta
from config import settings

THREADS = "https://graph.threads.net"


def env() -> dict:
    return envfile.read()


def save(values: dict[str, str]) -> None:
    envfile.set_values(values)
    v = env()  # the running app reads these settings: update them now, including a token that was cleared
    settings.meta_access_token = v.get("META_ACCESS_TOKEN", "")
    settings.threads_access_token = v.get("THREADS_ACCESS_TOKEN", "")


def _message(r: httpx.Response) -> str:
    try:
        return (r.json().get("error") or {}).get("message") or r.text[:200]
    except ValueError:
        return r.text[:200]


async def meta_debug(token: str) -> dict:
    """Meta's own answer about a token: valid, expires_at (0 = never), app_id, scopes. Never raises."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{meta.HOST}/debug_token", params={"input_token": token, "access_token": token})
    if r.status_code >= 400:
        return {"is_valid": False, "error": _message(r)}
    d = r.json().get("data", {})
    return {"is_valid": bool(d.get("is_valid")), "expires_at": d.get("expires_at", 0), "data_access_expires_at": d.get("data_access_expires_at", 0),
            "app_id": str(d.get("app_id", "")), "scopes": d.get("scopes", []), "error": (d.get("error") or {}).get("message", "")}


async def meta_long(token: str, app_id: str, secret: str) -> tuple[str, int | None]:
    """Swap a short Meta user token for a long one (about 60 days). Returns (token, expires_at or None)."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{meta.HOST}/{settings.meta_graph_version}/oauth/access_token",
                        params={"grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": secret, "fb_exchange_token": token})
    if r.status_code >= 400:
        raise meta.MetaError(f"Meta would not make a long token: {_message(r)}. Check the App ID and App secret (App settings, Basic).", 422)
    d = r.json()
    return d["access_token"], (int(time.time()) + int(d["expires_in"])) if d.get("expires_in") else None


async def threads_me(token: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{THREADS}/v1.0/me", params={"fields": "id,username", "access_token": token})
    return {"ok": True, **r.json()} if r.status_code < 400 else {"ok": False, "error": _message(r)}


async def threads_long(token: str, secret: str) -> tuple[str, int]:
    """Swap a short Threads token for a long one (60 days). Returns (token, expires_at)."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{THREADS}/access_token", params={"grant_type": "th_exchange_token", "client_secret": secret, "access_token": token})
    if r.status_code >= 400:
        raise meta.MetaError(f"Threads would not make a long token: {_message(r)}. Check the Threads app secret (Use cases, Threads, Settings).", 422)
    d = r.json()
    return d["access_token"], int(time.time()) + int(d.get("expires_in", 60 * 86400))
