"""Polymarket adapter - public gamma API, no wallet, no trades."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any

from scripts.lib.market_providers.base import MarketDataProvider

GAMMA_URL = "https://gamma-api.polymarket.com/markets"


class PolymarketProvider(MarketDataProvider):
    provider_id = "polymarket"

    def fetch_prediction_markets(self, *, query: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        params = f"?limit={limit}&active=true"
        if query:
            params += f"&slug={query}"
        url = GAMMA_URL + params
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TheTechBriefing-Market/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []

        markets = raw if isinstance(raw, list) else raw.get("markets", [])
        ts = datetime.now(timezone.utc).isoformat()
        out: list[dict] = []
        for m in markets[:limit]:
            out.append(self.normalize_market({**m, "timestamp": ts}))
        return out

    def fetch_market_quotes(self, market_ids: list[str]) -> list[dict[str, Any]]:
        return []

    @staticmethod
    def normalize_market(raw: dict[str, Any]) -> dict[str, Any]:
        outcomes = raw.get("outcomes") or raw.get("outcomePrices")
        return {
            "provider": "polymarket",
            "market_id": raw.get("id") or raw.get("conditionId") or raw.get("market_id"),
            "question": raw.get("question") or raw.get("title"),
            "outcomes": outcomes,
            "price": raw.get("lastTradePrice") or raw.get("price"),
            "volume": raw.get("volume") or raw.get("volumeNum"),
            "liquidity": raw.get("liquidity") or raw.get("liquidityNum"),
            "spread": raw.get("spread"),
            "timestamp": raw.get("timestamp") or raw.get("updatedAt"),
            "resolution_timestamp": raw.get("endDate") or raw.get("resolution_timestamp"),
            "status": raw.get("active", raw.get("status")),
            "source_url": raw.get("url") or f"https://polymarket.com/event/{raw.get('slug', '')}",
            "market_implied_probability": raw.get("lastTradePrice"),
            "model_estimate": None,
            "historical_frequency": None,
            "sample_size": None,
            "confidence": None,
            "methodology": "polymarket_gamma_api",
        }
