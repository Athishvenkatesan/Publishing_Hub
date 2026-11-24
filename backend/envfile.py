"""Change values in backend/.env from the screen (tokens, YouTube accounts set in .env). Keeps every other line and comment as it is."""
import re

from dotenv import dotenv_values

from config import HERE

ENV = HERE / ".env"


def read(path=None) -> dict:
    try:
        return {k: v or "" for k, v in dotenv_values(path or ENV).items()}
    except OSError:
        return {}


def set_values(values: dict[str, str], path=None) -> None:
    """Replace each NAME=... line (or add it at the end). Values must be one line."""
    path = path or ENV
    try:
        lines = path.read_text().splitlines()
    except OSError:
        lines = []
    for name, value in values.items():
        value = str(value).strip()
        if "\n" in value or "\r" in value:
            raise ValueError(f"{name} must be a single line.")
        pat = re.compile(rf"^\s*{re.escape(name)}\s*=")
        hit = next((i for i, l in enumerate(lines) if pat.match(l)), None)
        if hit is None:
            lines.append(f"{name}={value}")
        else:
            lines[hit] = f"{name}={value}"
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)  # holds secrets


def remove_names(names: list[str], path=None) -> None:
    """Delete each NAME=... line. Every other line and comment stays as it is."""
    path = path or ENV
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return
    pats = [re.compile(rf"^\s*{re.escape(n)}\s*=") for n in names]
    path.write_text("\n".join(l for l in lines if not any(p.match(l) for p in pats)) + "\n")
    path.chmod(0o600)
