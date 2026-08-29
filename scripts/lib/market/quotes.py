"""Free public market quote fetchers ($0/month)."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any


def _get_json(url: str, timeout: int = 15) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "TheTechBriefing-Market/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_yahoo_quote(symbol: str, *, market_id: str, asset_id: str) -> dict | None:
    """Yahoo Finance chart endpoint - public, no API key."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    try:
        data = _get_json(url)
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            return None
        meta = result[0].get("meta") or {}
        ts = datetime.now(timezone.utc).isoformat()
        return {
            "observation_id": f"price-{asset_id}-{int(datetime.now(timezone.utc).timestamp())}",
            "asset_id": asset_id,
            "market_id": market_id,
            "symbol": symbol,
            "timestamp": ts,
            "source": "yahoo_finance_chart",
            "source_url": url,
            "price": {
                "open": meta.get("regularMarketOpen"),
                "high": meta.get("regularMarketDayHigh"),
                "low": meta.get("regularMarketDayLow"),
                "close": meta.get("regularMarketPrice"),
                "previous_close": meta.get("chartPreviousClose"),
                "volume": meta.get("regularMarketVolume"),
            },
            "currency": meta.get("currency", "USD"),
            "bid": None,
            "ask": None,
            "spread": None,
            "order_flow": None,
        }
    except Exception:
        return None


def fetch_coingecko_quote(coin_id: str, *, market_id: str, asset_id: str) -> dict | None:
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coin_id}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true"
    )
    try:
        data = _get_json(url)
        coin = data.get(coin_id)
        if not coin:
            return None
        ts = datetime.now(timezone.utc).isoformat()
        return {
            "observation_id": f"price-{asset_id}-{int(datetime.now(timezone.utc).timestamp())}",
            "asset_id": asset_id,
            "market_id": market_id,
            "symbol": asset_id.upper(),
            "timestamp": ts,
            "source": "coingecko",
            "source_url": url,
            "price": {
                "close": coin.get("usd"),
                "volume": coin.get("usd_24h_vol"),
                "change_24h_pct": coin.get("usd_24h_change"),
            },
            "currency": "USD",
            "bid": None,
            "ask": None,
            "spread": None,
            "order_flow": None,
        }
    except Exception:
        return None


def fetch_all_quotes(assets: list[dict], markets: list[dict]) -> list[dict]:
    market_by_asset = {m["asset_id"]: m for m in markets}
    observations: list[dict] = []
    yahoo_symbols = {"nvda", "tsm", "msft", "goog", "aapl", "amzn", "meta", "intc", "amd"}
    for asset in assets:
        aid = asset["asset_id"]
        market = market_by_asset.get(aid)
        if not market:
            continue
        if aid == "btc":
            obs = fetch_coingecko_quote("bitcoin", market_id=market["market_id"], asset_id=aid)
        elif asset.get("symbol", "").lower() in yahoo_symbols or aid in yahoo_symbols:
            sym = asset.get("symbol", aid.upper())
            obs = fetch_yahoo_quote(sym, market_id=market["market_id"], asset_id=aid)
        else:
            obs = None
        if obs:
            observations.append(obs)
    return observations
