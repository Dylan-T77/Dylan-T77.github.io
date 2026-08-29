"""Structured RSS/Atom source definitions."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.lib.paths import INGEST_SOURCES_PATH

PIPELINE = [
    "SOURCES",
    "INGEST",
    "NORMALIZE",
    "VALIDATE",
    "DEDUPLICATE",
    "CLASSIFY",
    "EXTRACT EVENTS",
    "EDITORIAL REVIEW",
    "PUBLISH",
    "CONNECT",
]


def load_sources(path: Path = INGEST_SOURCES_PATH) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [s for s in payload.get("sources", []) if s.get("enabled", True)]


def source_by_id(sources: list[dict]) -> dict[str, dict]:
    return {s["source_id"]: s for s in sources}
