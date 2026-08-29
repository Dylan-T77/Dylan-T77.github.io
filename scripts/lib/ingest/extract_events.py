"""Rule-based event extraction with entity, country, and asset enrichment."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from scripts.lib.ingest.extract_entities import enrich_article
from scripts.lib.intelligence.comparables import comparable_features_for_event

EVENT_RULES: list[tuple[str, list[str]]] = [
    ("security_incident", ["breach", "ransomware", "vulnerability", "exploit", "zero-day", "malware", "cve-"]),
    ("regulatory_action", ["regulator", "regulation", "court rules", "antitrust", "ban ", " fined ", " gdpr"]),
    ("government_action", ["government", "congress", "senate", "white house", "federal", "eu ", "nasa"]),
    ("acquisition", ["acquires", "acquisition", "merger", "buyout", "to buy "]),
    ("funding", ["raises $", "funding round", "series a", "series b", "seed round", "venture"]),
    ("partnership", ["partners with", "partnership", "collaborat", "teams up"]),
    ("product_launch", ["launch", "launches", "unveil", "introduces", "debuts"]),
    ("infrastructure_investment", ["infrastructure", "data center", "data centre", "fab ", "foundry", "invest $"]),
    ("earnings", ["earnings", "revenue", "quarterly results", " beats ", " misses "]),
    ("research_result", ["researchers", "study finds", "paper ", "benchmark"]),
    ("technology_milestone", ["breakthrough", "milestone", "first ", "record "]),
    ("supply_chain_event", ["supply chain", "shortage", "export control", "sanction"]),
    ("market_event", ["stock", "shares", "market cap", "trading"]),
    ("macroeconomic_event", ["inflation", "interest rate", "gdp", "recession"]),
]

PRIORITY = {t: i for i, (t, _) in enumerate(EVENT_RULES)}


def event_id(article_id: str, fact: str) -> str:
    digest = hashlib.sha256(f"{article_id}|{fact[:120]}".encode()).hexdigest()[:16]
    return f"evt-{digest}"


def detect_event_types(title: str, summary: str) -> list[str]:
    hay = f" {title} {summary} ".lower()
    matched: list[str] = []
    for event_type, keywords in EVENT_RULES:
        if any(kw in hay for kw in keywords):
            matched.append(event_type)
    if not matched:
        matched.append("company_announcement")
    matched.sort(key=lambda t: PRIORITY.get(t, 99))
    return matched


def extract_facts(title: str, summary: str) -> list[str]:
    facts: list[str] = []
    if title:
        facts.append(title.strip())
    if summary and summary.strip() != title.strip():
        facts.append(summary.strip())
    return facts[:3]


def extract_event_from_article(article: dict) -> dict:
    enriched = enrich_article(article)
    title = enriched.get("title", "")
    summary = enriched.get("summary", "")
    extracted = enriched.get("extracted", {})
    event_types = detect_event_types(title, summary)
    facts = extract_facts(title, summary)
    ts = enriched.get("published_at") or enriched.get("ingested_at") or datetime.now(timezone.utc).isoformat()
    primary_type = event_types[0]
    geography = extracted.get("geography", {})

    country_ids = list(dict.fromkeys(
        geography.get("event_country_ids", [])
        + geography.get("regulatory_country_ids", [])
    ))

    evt = {
        "event_id": event_id(enriched["id"], facts[0] if facts else title),
        "event_type": primary_type,
        "event_types": event_types,
        "timestamp": ts,
        "source_ids": [enriched["source_id"]],
        "article_ids": [enriched["id"]],
        "companies": extracted.get("entity_ids", []),
        "entities": extracted.get("entity_ids", []),
        "countries": country_ids,
        "sectors": enriched.get("suggested_topics", []),
        "assets": extracted.get("assets", []),
        "amounts": extracted.get("amounts", []),
        "technologies": extracted.get("technologies", []),
        "geography": geography,
        "facts": facts,
        "confidence": "low" if enriched.get("source_category") == "aggregator" else "medium",
        "interpretation_status": "unreviewed",
        "interpretations": [],
        "hypotheses": [],
        "provenance": {
            "source_id": enriched["source_id"],
            "source_name": enriched["source"],
            "source_url": enriched.get("original_url"),
            "article_id": enriched["id"],
            "canonical_url": enriched["canonical_url"],
            "ingested_at": enriched.get("ingested_at"),
        },
    }
    evt["comparable_features"] = comparable_features_for_event(evt)
    return evt


def extract_all_events(articles: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for article in articles:
        evt = extract_event_from_article(article)
        by_id[evt["event_id"]] = evt
    return list(by_id.values())
