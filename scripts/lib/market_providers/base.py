"""Base interface for external market data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MarketDataProvider(ABC):
    provider_id: str

    @abstractmethod
    def fetch_prediction_markets(self, *, query: str | None = None) -> list[dict[str, Any]]:
        """Return normalized prediction-market observations."""

    @abstractmethod
    def fetch_market_quotes(self, market_ids: list[str]) -> list[dict[str, Any]]:
        """Return price/liquidity observations when available."""


class NullMarketDataProvider(MarketDataProvider):
    provider_id = "null"

    def fetch_prediction_markets(self, *, query: str | None = None) -> list[dict[str, Any]]:
        return []

    def fetch_market_quotes(self, market_ids: list[str]) -> list[dict[str, Any]]:
        return []
