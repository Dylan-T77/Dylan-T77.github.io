"""Derived price-action metrics from stored observations."""

from __future__ import annotations

from datetime import datetime, timezone


def compute_price_action(observation: dict, *, previous: dict | None = None) -> dict:
    price = observation.get("price") or {}
    close = price.get("close")
    prev_close = price.get("previous_close")
    if previous:
        prev_close = (previous.get("price") or {}).get("close") or prev_close

    derived: dict = {
        "observation_id": observation.get("observation_id"),
        "asset_id": observation.get("asset_id"),
        "timestamp": observation.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "source_observation": observation.get("observation_id"),
        "calculation": {},
    }

    if close is not None and prev_close not in (None, 0):
        ret = (close - prev_close) / prev_close
        derived["calculation"]["return_1d"] = round(ret, 6)
        derived["calculation"]["price_change_1d"] = round(close - prev_close, 4)

    if close is not None:
        derived["calculation"]["close"] = close
    if prev_close is not None:
        derived["calculation"]["previous_close"] = prev_close

    high = price.get("high")
    low = price.get("low")
    if close is not None and high is not None and low not in (None, 0):
        derived["calculation"]["distance_from_day_high_pct"] = round((close - high) / high, 6)
        derived["calculation"]["distance_from_day_low_pct"] = round((close - low) / low, 6)

    vol = price.get("volume")
    if vol is not None:
        derived["calculation"]["volume"] = vol

    return derived
