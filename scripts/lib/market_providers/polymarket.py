"""Polymarket adapter — interface only; no trades, no paid API calls in Stage 3."""

from __future__ import annotations

from typing import Any

from scripts.lib.market_providers.base import MarketDataProvider


class PolymarketProvider(MarketDataProvider):
    """Adapter stub for prediction-market data.

    Future: call public Polymarket endpoints and normalize into
    data/intelligence/observations/prediction_markets.json.

    Stage 3 keeps the interface without live fetches ($0/month).
    """

    provider_id = "polymarket"

    def fetch_prediction_markets(self, *, query: str | None = None) -> list[dict[str, Any]]:
        return []

    def fetch_market_quotes(self, market_ids: list[str]) -> list[dict[str, Any]]:
        return []

    @staticmethod
    def normalize_market(raw: dict[str, Any]) -> dict[str, Any]:
        """Map a provider payload to the internal observation schema."""
        return {
            "provider": "polymarket",
            "market_id": raw.get("id") or raw.get("market_id"),
            "question": raw.get("question"),
            "outcome": raw.get("outcome"),
            "price": raw.get("price"),
            "volume": raw.get("volume"),
            "liquidity": raw.get("liquidity"),
            "spread": raw.get("spread"),
            "timestamp": raw.get("timestamp"),
            "resolution_timestamp": raw.get("resolution_timestamp"),
            "status": raw.get("status"),
            "source_url": raw.get("url"),
        }
