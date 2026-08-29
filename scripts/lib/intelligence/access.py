"""Internal read-only access layer for market intelligence data."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.lib.paths import (
    INTELLIGENCE_ARTICLES_PATH,
    INTELLIGENCE_ASSETS_PATH,
    INTELLIGENCE_EVENTS_PATH,
    INTELLIGENCE_MARKETS_PATH,
    INTELLIGENCE_REACTIONS_PATH,
    OBS_LIQUIDITY_PATH,
    OBS_ORDER_FLOW_PATH,
    OBS_PREDICTION_PATH,
    OBS_PRICE_PATH,
    OBS_PROBABILITIES_PATH,
    ROOT,
)


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _items(payload: dict, key: str) -> list[dict]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


class IntelligenceStore:
    """Query structured intelligence without exposing a public HTTP API."""

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root

    def latest_events(self, *, limit: int = 50) -> list[dict]:
        events = _items(_load(INTELLIGENCE_EVENTS_PATH), "events")
        return sorted(events, key=lambda e: e.get("timestamp") or "", reverse=True)[:limit]

    def events_for_asset(self, asset_id: str) -> list[dict]:
        return [e for e in self.latest_events(limit=10_000) if asset_id in e.get("assets", [])]

    def events_for_entity(self, entity_id: str) -> list[dict]:
        return [
            e
            for e in self.latest_events(limit=10_000)
            if entity_id in e.get("entities", []) or entity_id in e.get("companies", [])
        ]

    def events_for_country(self, country_id: str) -> list[dict]:
        return [e for e in self.latest_events(limit=10_000) if country_id in e.get("countries", [])]

    def articles(self) -> list[dict]:
        return _items(_load(INTELLIGENCE_ARTICLES_PATH), "articles")

    def assets(self) -> list[dict]:
        return _items(_load(INTELLIGENCE_ASSETS_PATH), "assets")

    def markets(self) -> list[dict]:
        return _items(_load(INTELLIGENCE_MARKETS_PATH), "markets")

    def price_observations(self, *, asset_id: str | None = None) -> list[dict]:
        obs = _items(_load(OBS_PRICE_PATH), "observations")
        if asset_id:
            return [o for o in obs if o.get("asset_id") == asset_id]
        return obs

    def liquidity_observations(self, *, market_id: str | None = None) -> list[dict]:
        obs = _items(_load(OBS_LIQUIDITY_PATH), "observations")
        if market_id:
            return [o for o in obs if o.get("market_id") == market_id]
        return obs

    def order_flow_observations(self, *, market_id: str | None = None) -> list[dict]:
        obs = _items(_load(OBS_ORDER_FLOW_PATH), "observations")
        if market_id:
            return [o for o in obs if o.get("market_id") == market_id]
        return obs

    def prediction_market_observations(self) -> list[dict]:
        return _items(_load(OBS_PREDICTION_PATH), "observations")

    def probability_observations(self) -> list[dict]:
        return _items(_load(OBS_PROBABILITIES_PATH), "observations")

    def historical_reactions(self, *, event_id: str | None = None, asset_id: str | None = None) -> list[dict]:
        reactions = _items(_load(INTELLIGENCE_REACTIONS_PATH), "reactions")
        if event_id:
            reactions = [r for r in reactions if r.get("event_id") == event_id]
        if asset_id:
            reactions = [r for r in reactions if r.get("asset_id") == asset_id]
        return reactions
