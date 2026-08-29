"""Build public intelligence snapshot for the static site."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.intelligence.access import IntelligenceStore
from scripts.lib.paths import INTELLIGENCE_PUBLIC_PATH, ROOT


def build_intelligence_public(root: Path = ROOT) -> dict:
    store = IntelligenceStore(root)
    events = store.latest_events(limit=100)
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "freshness": {
                "articles": "moderate",
                "events": "persistent",
                "reactions": "persistent",
                "price_observations": "short_lived",
                "country_geometry": "static",
            },
            "counts": {
                "events": len(events),
                "articles": len(store.articles()),
                "assets": len(store.assets()),
                "markets": len(store.markets()),
                "reactions": len(store.historical_reactions()),
            },
        },
        "events": events[:24],
        "assets": store.assets(),
        "markets": store.markets(),
        "recent_articles": store.articles()[:12],
    }


def write_intelligence_public(root: Path = ROOT) -> Path:
    payload = build_intelligence_public(root)
    INTELLIGENCE_PUBLIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    INTELLIGENCE_PUBLIC_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return INTELLIGENCE_PUBLIC_PATH
