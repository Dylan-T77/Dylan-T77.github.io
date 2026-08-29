"""Build public intelligence snapshot for the static site."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.ingest.sectors import SECTOR_LABELS
from scripts.lib.intelligence.access import IntelligenceStore
from scripts.lib.intelligence.country_events import country_event_summary
from scripts.lib.paths import INTELLIGENCE_PUBLIC_PATH, ROOT


def build_intelligence_public(root: Path = ROOT) -> dict:
    store = IntelligenceStore(root)
    events = store.latest_events(limit=500)
    articles = store.articles()
    sector_counts: Counter[str] = Counter()
    for a in articles:
        ps = a.get("primary_sector")
        if ps:
            sector_counts[ps] += 1
        for s in a.get("suggested_topics", []):
            sector_counts[s] += 1

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": 2,
            "freshness": {
                "articles": "moderate",
                "events": "persistent",
                "reactions": "persistent",
                "price_observations": "short_lived",
                "country_geometry": "static",
            },
            "counts": {
                "events": len(events),
                "articles": len(articles),
                "assets": len(store.assets()),
                "markets": len(store.markets()),
                "reactions": len(store.historical_reactions()),
                "price_observations": len(store.price_observations()),
                "prediction_markets": len(store.prediction_market_observations()),
                "probabilities": len(store.probability_observations()),
                "countries_with_events": len(country_event_summary(events)),
            },
            "sectors": [
                {"id": sid, "label": SECTOR_LABELS.get(sid, sid), "count": n}
                for sid, n in sector_counts.most_common()
            ],
        },
        "events": events[:48],
        "assets": store.assets(),
        "markets": store.markets(),
        "articles": articles[:120],
        "country_events": country_event_summary(events),
        "price_observations": store.price_observations(),
        "reactions": store.historical_reactions()[:50],
        "probabilities": store.probability_observations()[:20],
    }


def write_intelligence_public(root: Path = ROOT) -> Path:
    payload = build_intelligence_public(root)
    INTELLIGENCE_PUBLIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    INTELLIGENCE_PUBLIC_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return INTELLIGENCE_PUBLIC_PATH
