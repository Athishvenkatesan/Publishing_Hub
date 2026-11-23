"""The X accounts this app can post to. Each account is one X app (OAuth 2.0 client ID + secret) and one X user sign-in.
Accounts are added on the X screen and saved in backend/x_accounts.json (git-ignored, mode 600).
Same shape as li_accounts.py (kept separate so each platform's files, limits and wording stay apart).
A request picks its account with ?account=key; code below reads the chosen account through current()."""
import json
import re
from contextvars import ContextVar
from dataclasses import dataclass, replace
from pathlib import Path

from config import HERE

TOKENS_DIR = HERE / "x_tokens"  # one sign-in file per account: git-ignored, keep private
ACCOUNTS_FILE = HERE / "x_accounts.json"
CLIENT_ID = re.compile(r"^[A-Za-z0-9_-]{16,80}$")
_chosen: ContextVar[str] = ContextVar("x_account", default="")


@dataclass(frozen=True)
class Account:
    key: str
    label: str
    client_id: str
    client_secret: str
    client_from: str = ""      # another X user on the same X app: uses that account's client instead of its own

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


def _read_file() -> list[dict]:
    try:
        d = json.loads(ACCOUNTS_FILE.read_text())
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _write_file(items: list[dict]) -> None:
    ACCOUNTS_FILE.write_text(json.dumps(items, indent=2))
    ACCOUNTS_FILE.chmod(0o600)  # holds client secrets


def load() -> dict[str, Account]:
    out = {i["key"]: Account(i["key"], i.get("label") or i["key"], i.get("client_id", ""), i.get("client_secret", ""), i.get("client_from", ""))
           for i in _read_file() if i.get("key")}
    for key, a in list(out.items()):  # resolve "same X app as ..." to the real client
        if a.client_from in out and a.client_from != key:
            src = out[a.client_from]
            out[key] = replace(a, client_id=src.client_id, client_secret=src.client_secret)
    return out


def default_key() -> str:
    return next(iter(load()), "")


def use(key: str | None, strict: bool = True) -> str:
    """Choose the account for the current request. strict=False falls back to the first one."""
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
    return accounts.get(_chosen.get() or next(iter(accounts), "")) or Account("", "", "", "")


def token_path(key: str) -> Path:
    return TOKENS_DIR / f"{key}.json"


def _slug(label: str, taken: set[str]) -> str:
    head = label.split("@")[0] or label.lstrip("@")
    base = re.sub(r"[^a-z0-9]+", "", head.lower())[:24] or "account"
    key, n = base, 2
    while key in taken:
        key, n = f"{base}{n}", n + 1
    return key


def _label(label: str) -> str:
    label = label.strip()
    if not label or len(label) > 60:
        raise ValueError("Give the account a name or email, up to 60 characters.")
    return label


def _client(client_id: str, secret: str) -> tuple[str, str]:
    client_id, secret = client_id.strip(), secret.strip()
    if not CLIENT_ID.match(client_id):
        raise ValueError("Paste the OAuth 2.0 Client ID from your X app (Keys and tokens). It is a long string of letters, digits, - and _.")
    if len(secret) < 8:
        raise ValueError("Paste the OAuth 2.0 Client Secret from your X app (Keys and tokens).")
    return client_id, secret


def add(label: str, client_id: str = "", client_secret: str = "", client_from: str = "") -> Account:
    accounts = load()
    label, client_from = _label(label), client_from.strip().lower()
    if client_from:
        if client_from not in accounts:
            raise ValueError("The X app you chose to reuse does not exist.")
        client_id = client_secret = ""
    else:
        client_id, client_secret = _client(client_id, client_secret)
    key = _slug(label, set(accounts))
    _write_file(_read_file() + [{"key": key, "label": label, "client_id": client_id, "client_secret": client_secret, "client_from": client_from}])
    return load()[key]


def update(key: str, label: str | None = None, client_id: str | None = None, client_secret: str | None = None) -> Account:
    items = _read_file()
    item = next((i for i in items if i.get("key") == key), None)
    if not item:
        raise KeyError(key)
    if label is not None:
        item["label"] = _label(label)
    if (client_id or client_secret) and not item.get("client_from"):
        item["client_id"], item["client_secret"] = _client(client_id or item["client_id"], client_secret or item["client_secret"])
    _write_file(items)
    return load()[key]


def remove(key: str) -> None:
    accounts = load()
    if key not in accounts:
        raise KeyError(key)
    if any(a.client_from == key for a in accounts.values()):
        raise ValueError("Other accounts use this account's X app. Remove them first.")
    _write_file([i for i in _read_file() if i.get("key") != key])
    token_path(key).unlink(missing_ok=True)
