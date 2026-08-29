"""Repository paths used by the static site build."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "network.json"
ASSET_MANIFEST_PATH = ROOT / "data" / "asset-manifest.json"
XENO_MAIN = ROOT / "scripts" / "xeno_signal_main.html"
RSS_INBOX_PATH = ROOT / "data" / "ingest" / "rss-inbox.json"
INGEST_SOURCES_PATH = ROOT / "data" / "ingest" / "sources.json"
ENTITY_REGISTRY_PATH = ROOT / "data" / "intelligence" / "entity-registry.json"
INTELLIGENCE_ARTICLES_PATH = ROOT / "data" / "intelligence" / "articles.json"
INTELLIGENCE_ARTICLES_ARCHIVE_PATH = ROOT / "data" / "intelligence" / "articles-archive.json"
INTELLIGENCE_EVENTS_PATH = ROOT / "data" / "intelligence" / "events.json"
INTELLIGENCE_ASSETS_PATH = ROOT / "data" / "intelligence" / "assets.json"
INTELLIGENCE_MARKETS_PATH = ROOT / "data" / "intelligence" / "markets.json"
INTELLIGENCE_REACTIONS_PATH = ROOT / "data" / "intelligence" / "reactions.json"
INTELLIGENCE_PRICE_ACTION_PATH = ROOT / "data" / "intelligence" / "price-action.json"
INTELLIGENCE_PUBLIC_PATH = ROOT / "data" / "intelligence.json"
OBS_PRICE_PATH = ROOT / "data" / "intelligence" / "observations" / "price.json"
OBS_LIQUIDITY_PATH = ROOT / "data" / "intelligence" / "observations" / "liquidity.json"
OBS_ORDER_FLOW_PATH = ROOT / "data" / "intelligence" / "observations" / "order_flow.json"
OBS_PREDICTION_PATH = ROOT / "data" / "intelligence" / "observations" / "prediction_markets.json"
OBS_PROBABILITIES_PATH = ROOT / "data" / "intelligence" / "observations" / "probabilities.json"
VOXEL_COUNTRIES_PATH = ROOT / "data" / "geo" / "voxel-countries.v1.json"
VOXEL_WORLD_PATH = ROOT / "data" / "geo" / "voxel-world.v1.json"
