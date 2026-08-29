"""Stable JSON writes — skip churn when only volatile metadata changed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _strip_volatile(value: Any, keys: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {k: _strip_volatile(v, keys) for k, v in value.items() if k not in keys}
    if isinstance(value, list):
        return [_strip_volatile(item, keys) for item in value]
    return value


def write_if_changed(
    path: Path,
    payload: dict,
    *,
    volatile_keys: frozenset[str] = frozenset({"generated_at"}),
) -> bool:
    """Write JSON when semantic content differs. Returns True if the file was updated."""
    new_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing = None
        if existing is not None:
            if _strip_volatile(existing, volatile_keys) == _strip_volatile(payload, volatile_keys):
                return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    return True
