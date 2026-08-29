"""Article retention and archive merge."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.lib.paths import INTELLIGENCE_ARTICLES_ARCHIVE_PATH, INGEST_SOURCES_PATH


def _load_policy() -> dict:
    payload = json.loads(INGEST_SOURCES_PATH.read_text(encoding="utf-8"))
    return payload.get("policy", {})


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def load_archive(path: Path = INTELLIGENCE_ARTICLES_ARCHIVE_PATH) -> list[dict]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("articles", [])
    except (OSError, ValueError, json.JSONDecodeError):
        return []


def merge_and_retain(
    new_items: list[dict],
    *,
    archive_path: Path = INTELLIGENCE_ARTICLES_ARCHIVE_PATH,
) -> tuple[list[dict], list[dict]]:
    """Merge new fetch with archive; return (active articles, full archive trimmed)."""
    policy = _load_policy()
    max_active = int(policy.get("max_active_articles", 600))
    archive_max = int(policy.get("archive_max_articles", 2500))
    retention_days = int(policy.get("archive_retention_days", 90))
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    by_url: dict[str, dict] = {}
    for item in load_archive(archive_path):
        by_url[item["canonical_url"]] = item
    for item in new_items:
        existing = by_url.get(item["canonical_url"])
        if existing:
            item = {**existing, **item, "last_seen_at": item.get("ingested_at")}
        else:
            item = {**item, "first_seen_at": item.get("ingested_at"), "last_seen_at": item.get("ingested_at")}
        by_url[item["canonical_url"]] = item

    all_items = list(by_url.values())
    all_items.sort(
        key=lambda a: _parse_ts(a.get("published_at") or a.get("ingested_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    trimmed: list[dict] = []
    for item in all_items:
        ts = _parse_ts(item.get("published_at") or item.get("ingested_at"))
        if ts and ts < cutoff:
            continue
        trimmed.append(item)
    if len(trimmed) > archive_max:
        trimmed = trimmed[:archive_max]

    active = trimmed[:max_active]
    return active, trimmed


def write_archive(articles: list[dict], path: Path = INTELLIGENCE_ARTICLES_ARCHIVE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "moderate",
        "articles": articles,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
