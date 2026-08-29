"""HTML helpers and filesystem utilities for page generation."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path

from scripts.lib.paths import DATA_PATH, ROOT


def e(value) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def load() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def index_by(items: list[dict], key: str = "id") -> dict:
    return {item[key]: item for item in items}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def page_file(route: str) -> Path:
    route = route.rstrip("/") or ""
    if route == "":
        return ROOT / "index.html"
    if route.endswith(".html"):
        return ROOT / route.lstrip("/")
    return ROOT / route.lstrip("/") / "index.html"


def pretty_date(value: str | None) -> str:
    if not value:
        return "undated"
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d %b %Y").upper()
    except ValueError:
        return value


def short_date(value: str | None) -> str:
    if not value:
        return "UNDATED"
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d %b").upper()
    except ValueError:
        return value
