"""Deduplicate normalized records by canonical URL."""

from __future__ import annotations


def dedupe_items(items: list[dict]) -> list[dict]:
    unique: list[dict] = []
    seen: set[str] = set()
    for item in items:
        key = item["canonical_url"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
