#!/usr/bin/env python3
"""Run the full editorial ingestion and intelligence enrichment pipeline."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.ingest.dedupe import dedupe_items
from scripts.lib.ingest.extract_entities import enrich_article
from scripts.lib.ingest.extract_events import extract_all_events
from scripts.lib.ingest.normalize import normalize_all
from scripts.lib.ingest.retention import merge_and_retain, write_archive
from scripts.lib.ingest.sources import PIPELINE, load_sources
from scripts.lib.ingest.validate import validate_items
from scripts.lib.market.price_action import compute_price_action
from scripts.lib.market.quotes import fetch_all_quotes
from scripts.lib.market.reactions import build_reactions_for_event
from scripts.lib.market_providers.polymarket import PolymarketProvider
from scripts.lib.paths import (
    INTELLIGENCE_ARTICLES_PATH,
    INTELLIGENCE_ASSETS_PATH,
    INTELLIGENCE_EVENTS_PATH,
    INTELLIGENCE_MARKETS_PATH,
    INTELLIGENCE_PRICE_ACTION_PATH,
    INTELLIGENCE_REACTIONS_PATH,
    OBS_PREDICTION_PATH,
    OBS_PRICE_PATH,
    OBS_PROBABILITIES_PATH,
    RSS_INBOX_PATH,
)


def _load_json(path: Path, key: str) -> list:
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get(key, [])


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    sources = load_sources()
    raw_items, ingest_errors = normalize_all(sources)
    valid_items, validation_errors = validate_items(raw_items)
    unique_new = dedupe_items(valid_items)
    active_articles, archive_articles = merge_and_retain(unique_new)
    write_archive(archive_articles)

    enriched_articles = [enrich_article(a) for a in active_articles]
    events = extract_all_events(enriched_articles)
    generated_at = datetime.now(timezone.utc).isoformat()

    assets = _load_json(INTELLIGENCE_ASSETS_PATH, "assets")
    markets = _load_json(INTELLIGENCE_MARKETS_PATH, "markets")
    price_obs = fetch_all_quotes(assets, markets)
    symbol_by_asset = {a["asset_id"]: a.get("symbol", a["asset_id"].upper()) for a in assets}

    prev_prices = _load_json(OBS_PRICE_PATH, "observations")
    prev_by_asset = {p["asset_id"]: p for p in prev_prices}
    price_actions = [compute_price_action(o, previous=prev_by_asset.get(o["asset_id"])) for o in price_obs]

    existing_reactions = _load_json(INTELLIGENCE_REACTIONS_PATH, "reactions")
    new_reactions: list[dict] = []
    for event in events:
        for asset_id in event.get("assets", []):
            sym = symbol_by_asset.get(asset_id)
            if sym:
                new_reactions.extend(build_reactions_for_event(event, asset_id, sym, existing_reactions + new_reactions))
    all_reactions = existing_reactions + new_reactions

    polymarket = PolymarketProvider()
    prediction_obs = polymarket.fetch_prediction_markets(limit=20)
    probabilities = [
        {
            "observation_id": f"prob-{p.get('market_id', i)}",
            "timestamp": p.get("timestamp"),
            "source": "polymarket_gamma_api",
            "methodology": "market_implied_probability",
            "market_implied_probability": p.get("market_implied_probability"),
            "historical_frequency": None,
            "model_estimate": None,
            "sample_size": None,
            "confidence": None,
            "market_id": p.get("market_id"),
            "question": p.get("question"),
        }
        for i, p in enumerate(prediction_obs)
        if p.get("market_implied_probability") is not None
    ]

    _write_json(RSS_INBOX_PATH, {
        "generated_at": generated_at,
        "pipeline": PIPELINE,
        "policy": {"auto_publish": False, "editorial_state": "INBOX"},
        "errors": ingest_errors + validation_errors,
        "items": active_articles,
    })
    _write_json(INTELLIGENCE_ARTICLES_PATH, {
        "version": 2,
        "generated_at": generated_at,
        "freshness": "moderate",
        "articles": enriched_articles,
    })
    _write_json(INTELLIGENCE_EVENTS_PATH, {
        "version": 2,
        "generated_at": generated_at,
        "freshness": "persistent",
        "events": events,
    })
    _write_json(OBS_PRICE_PATH, {
        "version": 1,
        "generated_at": generated_at,
        "freshness": "short_lived",
        "observations": price_obs,
    })
    _write_json(INTELLIGENCE_PRICE_ACTION_PATH, {
        "version": 1,
        "generated_at": generated_at,
        "observations": price_actions,
    })
    _write_json(INTELLIGENCE_REACTIONS_PATH, {
        "version": 1,
        "generated_at": generated_at,
        "freshness": "persistent",
        "policy": {"windows": ["5m", "15m", "1h", "4h", "1d", "1w"], "note": "Observational only."},
        "reactions": all_reactions,
    })
    _write_json(OBS_PREDICTION_PATH, {
        "version": 1,
        "generated_at": generated_at,
        "observations": prediction_obs,
    })
    _write_json(OBS_PROBABILITIES_PATH, {
        "version": 1,
        "generated_at": generated_at,
        "observations": probabilities,
    })

    if True in {item["publish"] for item in active_articles}:
        raise SystemExit("Invariant violated: inbox item marked publish=true")

    print(f"Sources: {len(sources)} enabled | New fetch: {len(unique_new)} | Active articles: {len(active_articles)} | Archive: {len(archive_articles)}")
    print(f"Events: {len(events)} | Price observations: {len(price_obs)} | Reactions: {len(all_reactions)} (+{len(new_reactions)})")
    print(f"Prediction markets: {len(prediction_obs)} | Probabilities: {len(probabilities)}")
    if ingest_errors:
        print(f"Source errors: {len(ingest_errors)}")


if __name__ == "__main__":
    main()
