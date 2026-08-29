"""Rule-based event extraction from normalized information records."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

EVENT_RULES: list[tuple[str, list[str]]] = [
    ("security_incident", ["breach", "ransomware", "vulnerability", "exploit", "zero-day", "malware", "cve-"]),
    ("regulatory_action", ["regulator", "regulation", "court rules", "antitrust", "ban ", " fined "]),
    ("government_action", ["government", "congress", "senate", "white house", "federal", "eu "]),
    ("acquisition", ["acquires", "acquisition", "merger", "buyout", "to buy "]),
    ("funding", ["raises $", "funding round", "series a", "series b", "seed round", "venture"]),
    ("partnership", ["partners with", "partnership", "collaborat", "teams up"]),
    ("product_launch", ["launch", "launches", "unveil", "introduces", "debuts"]),
    ("infrastructure_investment", ["infrastructure", "data center", "fab ", "foundry", "invest $", "investment"]),
    ("earnings", ["earnings", "revenue", "quarterly results", " beats ", " misses "]),
    ("research_result", ["researchers", "study finds", "paper ", "benchmark"]),
    ("technology_milestone", ["breakthrough", "milestone", "first ", "record "]),
    ("supply_chain_event", ["supply chain", "shortage", "export control", "sanction"]),
    ("market_event", ["stock", "shares", "market cap", "trading"]),
    ("macroeconomic_event", ["inflation", "interest rate", "gdp", "recession"]),
    ("company_announcement", []),
]


def event_id(article_id: str, event_type: str, fact: str) -> str:
    digest = hashlib.sha256(f"{article_id}|{event_type}|{fact[:120]}".encode()).hexdigest()[:16]
    return f"evt-{digest}"


def detect_event_types(title: str, summary: str) -> list[str]:
    hay = f" {title} {summary} ".lower()
    matched: list[str] = []
    for event_type, keywords in EVENT_RULES:
        if not keywords:
            continue
        if any(kw in hay for kw in keywords):
            matched.append(event_type)
    if not matched:
        matched.append("company_announcement")
    return matched


def extract_facts(title: str, summary: str) -> list[str]:
    facts: list[str] = []
    if title:
        facts.append(title.strip())
    if summary and summary.strip() != title.strip():
        facts.append(summary.strip())
    return facts[:3]


def extract_events_from_article(article: dict) -> list[dict]:
    title = article.get("title", "")
    summary = article.get("summary", "")
    event_types = detect_event_types(title, summary)
    facts = extract_facts(title, summary)
    ts = article.get("published_at") or article.get("ingested_at") or datetime.now(timezone.utc).isoformat()
    events: list[dict] = []
    for event_type in event_types:
        primary_fact = facts[0] if facts else title
        evt = {
            "event_id": event_id(article["id"], event_type, primary_fact),
            "event_type": event_type,
            "timestamp": ts,
            "source_ids": [article["source_id"]],
            "article_ids": [article["id"]],
            "companies": article.get("suggested_entities", []),
            "entities": article.get("suggested_entities", []),
            "countries": [],
            "sectors": article.get("suggested_topics", []),
            "assets": [],
            "facts": facts,
            "confidence": "low" if article.get("source_category") == "aggregator" else "medium",
            "interpretation_status": "unreviewed",
            "interpretations": [],
            "hypotheses": [],
            "provenance": {
                "source_id": article["source_id"],
                "source_name": article["source"],
                "article_id": article["id"],
                "canonical_url": article["canonical_url"],
            },
        }
        events.append(evt)
    return events


def extract_all_events(articles: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for article in articles:
        for evt in extract_events_from_article(article):
            by_id[evt["event_id"]] = evt
    return list(by_id.values())
