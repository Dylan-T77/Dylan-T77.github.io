"""Aggregate intelligence events by country for the voxel map."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


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


def country_event_summary(events: list[dict], *, recent_days: int = 7) -> dict[str, dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)
    summary: dict[str, dict] = {}
    for ev in events:
        ts = _parse_ts(ev.get("timestamp"))
        for cid in ev.get("countries", []):
            row = summary.setdefault(cid, {"country_id": cid, "event_count": 0, "recent_count": 0})
            row["event_count"] += 1
            if ts and ts >= cutoff:
                row["recent_count"] += 1
    return summary
