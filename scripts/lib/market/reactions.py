"""Historical reaction dataset builder (observational, not predictive)."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone

REACTION_WINDOWS = ["5m", "15m", "1h", "4h", "1d", "1w"]

WINDOW_MINUTES = {
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
    "1w": 10080,
}


def _parse_ts(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _yahoo_chart(symbol: str, event_ts: datetime, window_min: int) -> list[dict]:
    """Fetch 1m or 5m bars around event if within Yahoo retention."""
    age = datetime.now(timezone.utc) - event_ts
    if age > timedelta(days=7):
        return []
    interval = "1m" if age <= timedelta(days=1) else "5m"
    period1 = int((event_ts - timedelta(hours=1)).timestamp())
    period2 = int((event_ts + timedelta(hours=26)).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval={interval}&period1={period1}&period2={period2}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "TheTechBriefing-Market/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            return []
        timestamps = result[0].get("timestamp") or []
        closes = ((result[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
        bars = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            bars.append({"timestamp": datetime.fromtimestamp(ts, tz=timezone.utc), "close": close})
        return bars
    except Exception:
        return []


def _price_at_offset(bars: list[dict], event_ts: datetime, offset_min: int) -> float | None:
    target = event_ts + timedelta(minutes=offset_min)
    best = None
    best_delta = None
    for bar in bars:
        delta = abs((bar["timestamp"] - target).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = bar["close"]
    return best


def build_reactions_for_event(
    event: dict,
    asset_id: str,
    symbol: str,
    existing: list[dict],
) -> list[dict]:
    if not event.get("assets") or asset_id not in event["assets"]:
        return []
    event_ts = _parse_ts(event.get("timestamp", ""))
    if not event_ts:
        return []

    existing_keys = {(r["event_id"], r["asset_id"], r["window"]) for r in existing}
    bars = _yahoo_chart(symbol, event_ts, 60)
    if len(bars) < 2:
        return []

    price_before = _price_at_offset(bars, event_ts, 0)
    if price_before is None:
        return []

    new_rows: list[dict] = []
    for window in REACTION_WINDOWS:
        key = (event["event_id"], asset_id, window)
        if key in existing_keys:
            continue
        offset = WINDOW_MINUTES[window]
        price_after = _price_at_offset(bars, event_ts, offset)
        if price_after is None or price_before == 0:
            continue
        ret = (price_after - price_before) / price_before
        obs_ts = (event_ts + timedelta(minutes=offset)).isoformat()
        new_rows.append({
            "reaction_id": f"rxn-{event['event_id']}-{asset_id}-{window}",
            "event_id": event["event_id"],
            "asset_id": asset_id,
            "event_timestamp": event_ts.isoformat(),
            "observation_timestamp": obs_ts,
            "window": window,
            "price_before": round(price_before, 6),
            "price_after": round(price_after, 6),
            "return": round(ret, 6),
            "source": "yahoo_finance_chart",
            "methodology": "nearest_bar_to_window_offset",
            "note": "Observational record only - not a trading signal.",
        })
    return new_rows
