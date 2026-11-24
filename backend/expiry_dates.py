"""Expiry dates people set on accounts (for example when a client secret or a token runs out), one place for every platform.
Saved in backend/account_expiry.json (git-ignored). Keyed "platform:account"."""
import json
from datetime import date

from config import HERE

FILE = HERE / "account_expiry.json"


def _all() -> dict:
    try:
        d = json.loads(FILE.read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def clean(value: str) -> str:
    """'' clears it; otherwise it must be a real date written YYYY-MM-DD."""
    value = (value or "").strip()
    if not value:
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError("The expiry date must be a date like 2027-01-31.")


def get(platform: str, key: str) -> str:
    return _all().get(f"{platform}:{key}", "")


def put(platform: str, key: str, value: str) -> str:
    value, d = clean(value), _all()
    if value:
        d[f"{platform}:{key}"] = value
    else:
        d.pop(f"{platform}:{key}", None)
    FILE.write_text(json.dumps(d, indent=2))
    return value


def info(platform: str, key: str) -> dict:
    """{"expires_on": "YYYY-MM-DD" or "", "days_left": int or None} for the account card."""
    value = get(platform, key)
    return {"expires_on": value, "days_left": (date.fromisoformat(value) - date.today()).days if value else None}
