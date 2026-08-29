"""Transparent comparable-event features for future research."""

from __future__ import annotations


def magnitude_bucket(amounts: list[dict]) -> str:
    if not amounts:
        return "unknown"
    usd = max(a.get("usd", 0) for a in amounts)
    if usd >= 1_000_000_000:
        return "billion_plus"
    if usd >= 10_000_000:
        return "ten_million_plus"
    if usd >= 1_000_000:
        return "million_plus"
    return "sub_million"


def comparable_features_for_event(event: dict) -> dict:
    return {
        "event_type": event.get("event_type"),
        "event_types": event.get("event_types", []),
        "entities": event.get("entities", []),
        "sectors": event.get("sectors", []),
        "countries": event.get("countries", []),
        "assets": event.get("assets", []),
        "has_amount": bool(event.get("amounts")),
        "magnitude_bucket": magnitude_bucket(event.get("amounts", [])),
        "technology_tags": event.get("technologies", []),
        "source_category": event.get("provenance", {}).get("source_id"),
    }


def find_comparable_events(target: dict, catalog: list[dict], *, limit: int = 10) -> list[dict]:
    feats = target.get("comparable_features") or comparable_features_for_event(target)
    scored: list[tuple[int, dict]] = []
    for candidate in catalog:
        if candidate.get("event_id") == target.get("event_id"):
            continue
        cf = candidate.get("comparable_features") or comparable_features_for_event(candidate)
        score = 0
        if cf.get("event_type") == feats.get("event_type"):
            score += 3
        score += len(set(cf.get("sectors", [])) & set(feats.get("sectors", [])))
        score += len(set(cf.get("entities", [])) & set(feats.get("entities", []))) * 2
        score += len(set(cf.get("countries", [])) & set(feats.get("countries", [])))
        if cf.get("magnitude_bucket") == feats.get("magnitude_bucket") and feats.get("magnitude_bucket") != "unknown":
            score += 1
        if score > 0:
            scored.append((score, candidate))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:limit]]
