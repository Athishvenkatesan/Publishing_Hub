"""The YouTube accounts this app can post to, read from backend/.env. Each account has its own Google client and its own sign-in.

    YOUTUBE_ACCOUNTS=first,second
    YOUTUBE_FIRST_LABEL=first@gmail.com
    YOUTUBE_FIRST_CLIENT_ID=...
    YOUTUBE_FIRST_CLIENT_SECRET=...
    (and the same three lines for SECOND)

With no YOUTUBE_ACCOUNTS, the older single pair YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET still works as one account called "main".
A request picks its account with ?account=key. Code below reads the chosen account through current()."""
import json
import os
import re
from contextvars import ContextVar
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import dotenv_values

import envfile
from config import HERE, settings

ENV_FILE = HERE / ".env"
TOKENS_DIR = HERE / "youtube_tokens"  # one refresh-token file per account: git-ignored, keep private
ACCOUNTS_FILE = HERE / "youtube_accounts.json"  # accounts added from the Accounts manager screen: git-ignored, keep private
CLIENT_ID = re.compile(r"^\d+-[\w-]+\.apps\.googleusercontent\.com$")
_chosen: ContextVar[str] = ContextVar("youtube_account", default="")


@dataclass(frozen=True)
class Account:
    key: str
    label: str
    client_id: str
    client_secret: str
    source: str = "env"        # env: set in backend/.env, read-only on screen. file: added on screen.
    client_from: str = ""      # another channel of the same Google app: uses that account's client instead of its own

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def fix_hint(self) -> str:
        """Where to correct this account's Google app, depending on how it was added."""
        if self.source == "file":
            return "Remove this account and add it again with the right client ID and secret."
        return f"Check {self.env_names} in backend/.env."

    @property
    def env_names(self) -> str:
        up = self.key.upper().replace("-", "_")
        return f"YOUTUBE_{up}_CLIENT_ID and YOUTUBE_{up}_CLIENT_SECRET"


def load() -> dict[str, Account]:
    """Every account named in YOUTUBE_ACCOUNTS (even one with missing values, so the screen can say what is missing)."""
    env = {**dotenv_values(ENV_FILE), **os.environ}
    out: dict[str, Account] = {}
    for key in [k.strip().lower() for k in (env.get("YOUTUBE_ACCOUNTS") or "").split(",") if k.strip()]:
        up = key.upper().replace("-", "_")
        out[key] = Account(key, env.get(f"YOUTUBE_{up}_LABEL") or key, env.get(f"YOUTUBE_{up}_CLIENT_ID") or "",
                           env.get(f"YOUTUBE_{up}_CLIENT_SECRET") or "")
    if not out and settings.youtube_client_id and settings.youtube_client_secret:
        out["main"] = Account("main", "YouTube channel", settings.youtube_client_id, settings.youtube_client_secret)
    for item in _read_file():
        key = item.get("key", "")
        if key and key not in out:  # .env wins if the same key appears in both
            out[key] = Account(key, item.get("label") or key, item.get("client_id", ""), item.get("client_secret", ""), "file", item.get("client_from", ""))
    for key, a in list(out.items()):  # resolve "same Google app as ..." to the real client
        if a.client_from and a.client_from in out and a.client_from != key:
            src = out[a.client_from]
            out[key] = replace(a, client_id=src.client_id, client_secret=src.client_secret)
    return out


def default_key() -> str:
    accounts = load()
    return next(iter(accounts), "")


def use(key: str | None, strict: bool = True) -> str:
    """Choose the account for the current request. strict=False falls back to the first one (older rows have no real account)."""
    accounts = load()
    chosen = (key or "").strip().lower()
    if chosen not in accounts:
        if chosen and strict:
            raise KeyError(chosen)
        chosen = next(iter(accounts), "")
    _chosen.set(chosen)
    return chosen


def current() -> Account:
    accounts = load()
    key = _chosen.get() or next(iter(accounts), "")
    return accounts.get(key) or Account("", "", "", "")


def token_path(key: str) -> Path:
    return TOKENS_DIR / f"{key}.json"


# ---------- accounts added from the screen ----------
def _read_file() -> list[dict]:
    try:
        d = json.loads(ACCOUNTS_FILE.read_text())
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _write_file(items: list[dict]) -> None:
    ACCOUNTS_FILE.write_text(json.dumps(items, indent=2))
    ACCOUNTS_FILE.chmod(0o600)  # holds client secrets


def _slug(label: str, taken: set[str]) -> str:
    head = label.split("@")[0] or label.lstrip("@")  # an email gives its name part, a handle like @Channel gives the handle
    base = re.sub(r"[^a-z0-9]+", "", head.lower())[:24] or "account"
    key, n = base, 2
    while key in taken:
        key, n = f"{base}{n}", n + 1
    return key


def _clean(label: str, client_id: str, secret: str, client_from: str, accounts: dict, own_key: str = "") -> tuple[str, str, str, str]:
    label, client_id, secret, client_from = label.strip(), client_id.strip(), secret.strip(), client_from.strip().lower()
    if not label or len(label) > 60:
        raise ValueError("Give the account a name or email, up to 60 characters.")
    if client_from:
        if client_from not in accounts or client_from == own_key:
            raise ValueError("The Google app you chose to reuse does not exist.")
        return label, "", "", client_from
    if not CLIENT_ID.match(client_id):
        raise ValueError("The client ID should look like 123456789-abc....apps.googleusercontent.com.")
    if len(secret) < 8:
        raise ValueError("Paste the client secret from Google Cloud.")
    return label, client_id, secret, ""


def add(label: str, client_id: str = "", client_secret: str = "", client_from: str = "") -> Account:
    accounts = load()
    label, client_id, secret, client_from = _clean(label, client_id, client_secret, client_from, accounts)
    key = _slug(label, set(accounts))
    _write_file(_read_file() + [{"key": key, "label": label, "client_id": client_id, "client_secret": secret, "client_from": client_from}])
    return load()[key]


def update(key: str, label: str | None = None, client_id: str | None = None, client_secret: str | None = None) -> Account:
    accounts, items = load(), _read_file()
    if key in accounts and accounts[key].source == "env":
        return _update_env(accounts[key], label, client_id, client_secret)
    item = next((i for i in items if i.get("key") == key), None)
    if not item or key not in accounts or accounts[key].source != "file":
        raise PermissionError("Only accounts added on screen can be changed here. Edit backend/.env for the others.")
    new_label = (item["label"] if label is None else label).strip()
    if not new_label or len(new_label) > 60:
        raise ValueError("Give the account a name or email, up to 60 characters.")
    item["label"] = new_label
    if not item.get("client_from"):  # an account that reuses another Google app has no client of its own to change
        cid, sec = (client_id or item["client_id"]).strip(), (client_secret or item["client_secret"]).strip()
        if not CLIENT_ID.match(cid) or len(sec) < 8:
            raise ValueError("The client ID or secret does not look right.")
        item["client_id"], item["client_secret"] = cid, sec
    _write_file(items)
    return load()[key]


def _update_env(a: Account, label: str | None, client_id: str | None, client_secret: str | None) -> Account:
    """An account set in backend/.env: write the changed values back to its YOUTUBE_<KEY>_... lines."""
    if a.key == "main" and not (dotenv_values(ENV_FILE).get("YOUTUBE_ACCOUNTS") or ""):
        raise PermissionError("This channel comes from YOUTUBE_CLIENT_ID in backend/.env. Edit that file to change it.")
    up, values = a.key.upper().replace("-", "_"), {}
    if label is not None:
        label = label.strip()
        if not label or len(label) > 60:
            raise ValueError("Give the account a name or email, up to 60 characters.")
        values[f"YOUTUBE_{up}_LABEL"] = label
    if client_id or client_secret:
        cid, sec = (client_id or a.client_id).strip(), (client_secret or a.client_secret).strip()
        if not CLIENT_ID.match(cid) or len(sec) < 8:
            raise ValueError("The client ID or secret does not look right.")
        values.update({f"YOUTUBE_{up}_CLIENT_ID": cid, f"YOUTUBE_{up}_CLIENT_SECRET": sec})
    if values:
        envfile.set_values(values, ENV_FILE)
    return load()[a.key]


def remove(key: str) -> None:
    accounts = load()
    if key not in accounts or accounts[key].source != "file":
        raise PermissionError("Only accounts added on screen can be removed here. Edit backend/.env for the others.")
    if any(a.client_from == key for a in accounts.values()):
        raise ValueError("Other channels use this account's Google app. Remove them first.")
    _write_file([i for i in _read_file() if i.get("key") != key])
    token_path(key).unlink(missing_ok=True)
