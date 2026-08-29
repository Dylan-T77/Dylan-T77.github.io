"""Entity, country, region, and amount extraction from article text."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.lib.paths import ENTITY_REGISTRY_PATH, ROOT
from scripts.lib.voxel_geo import COUNTRY_ALIASES, resolve_country_id

# Evidence-based event location patterns (country name or alias in text)
EVENT_LOCATION_MARKERS: list[tuple[str, list[str]]] = [
    ("United States of America", [" in texas", " in california", " in the u.s.", " in us ", " in america", " united states"]),
    ("United Kingdom", [" in the uk", " in britain", " in london", " united kingdom"]),
    ("China", [" in china", " chinese ", " beijing", " shanghai"]),
    ("Taiwan", [" in taiwan", " taipei"]),
    ("Germany", [" in germany", " berlin", " munich"]),
    ("France", [" in france", " paris"]),
    ("Japan", [" in japan", " tokyo"]),
    ("South Korea", [" in south korea", " in korea", " seoul"]),
    ("India", [" in india", " bangalore", " mumbai", " delhi"]),
    ("European Union", [" in the eu", " european union", " european commission"]),
]

REGULATORY_MARKERS: list[tuple[str, list[str]]] = [
    ("United States of America", [" sec ", " ftc ", " doj ", " u.s. government", " congress ", " senate "]),
    ("European Union", [" eu ", " european commission", " gdpr", " dma ", " antitrust in europe"]),
    ("United Kingdom", [" uk regulator", " ofcom", " competition and markets"]),
]

US_STATES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west virginia", "wisconsin", "wyoming",
]

AMOUNT_RE = re.compile(
    r"\$\s*([\d,.]+)\s*(billion|million|bn|m|b)?|\b([\d,.]+)\s*(billion|million)\s+dollars",
    re.I,
)

TECHNOLOGY_MARKERS = [
    "ai", "artificial intelligence", "gpu", "data center", "data centre", "quantum",
    "robotics", "cloud", "5g", "semiconductor", "llm", "cybersecurity", "blockchain",
]


def _load_registry(root: Path = ROOT) -> list[dict]:
    path = ENTITY_REGISTRY_PATH
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("entities", [])


def _load_voxel_countries(root: Path = ROOT) -> dict[str, dict]:
    from scripts.lib.paths import VOXEL_COUNTRIES_PATH

    if not VOXEL_COUNTRIES_PATH.is_file():
        return {}
    payload = json.loads(VOXEL_COUNTRIES_PATH.read_text(encoding="utf-8"))
    return {c["id"]: c for c in payload.get("countries", [])}


def extract_amounts(text: str) -> list[dict]:
    amounts: list[dict] = []
    for match in AMOUNT_RE.finditer(text):
        raw = match.group(1) or match.group(3)
        unit = (match.group(2) or match.group(4) or "").lower()
        if not raw:
            continue
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        if unit in {"billion", "b", "bn"}:
            value *= 1_000_000_000
        elif unit in {"million", "m"}:
            value *= 1_000_000
        amounts.append({"raw": match.group(0).strip(), "usd": value, "currency": "USD"})
    return amounts


def extract_regions(text: str) -> list[str]:
    hay = f" {text.lower()} "
    regions: list[str] = []
    for state in US_STATES:
        if f" in {state}" in hay or f" {state}," in hay:
            regions.append(state.title())
    return regions


def extract_technologies(text: str) -> list[str]:
    hay = f" {text.lower()} "
    return [t for t in TECHNOLOGY_MARKERS if f" {t} " in hay or t in hay]


def _match_location(markers: list[tuple[str, list[str]]], hay: str) -> list[str]:
    found: list[str] = []
    for country, keys in markers:
        if any(k in hay for k in keys):
            found.append(country)
    return found


def extract_geography(title: str, summary: str, entity_ids: list[str], registry: list[dict], voxel_countries: dict[str, dict]) -> dict:
    hay = f" {title} {summary} ".lower()
    event_locations = _match_location(EVENT_LOCATION_MARKERS, hay)
    regulatory = _match_location(REGULATORY_MARKERS, hay)

    headquarters: list[dict] = []
    for eid in entity_ids:
        for ent in registry:
            if ent["id"] == eid and ent.get("headquarters_country_id"):
                headquarters.append({
                    "entity_id": eid,
                    "country_id": ent["headquarters_country_id"],
                    "country_label": ent.get("headquarters_label"),
                    "location_type": "headquarters",
                    "evidence": "entity_registry",
                })

    event_country_ids: list[str] = []
    for label in event_locations:
        cid = resolve_country_id(label, voxel_countries)
        if cid and cid not in event_country_ids:
            event_country_ids.append(cid)

    regulatory_ids: list[str] = []
    for label in regulatory:
        cid = resolve_country_id(label, voxel_countries)
        if cid and cid not in regulatory_ids:
            regulatory_ids.append(cid)

    return {
        "headquarters": headquarters,
        "event_location_labels": event_locations,
        "event_country_ids": event_country_ids,
        "regulatory_jurisdiction_labels": regulatory,
        "regulatory_country_ids": regulatory_ids,
        "regions": extract_regions(hay),
        "market_location_country_ids": [],
    }


def extract_entities_from_text(title: str, summary: str, registry: list[dict] | None = None) -> list[dict]:
    registry = registry or _load_registry()
    hay = f" {title} {summary} ".lower()
    found: list[dict] = []
    for ent in registry:
        for name in ent.get("names", []):
            if f" {name.lower()} " in hay or name.lower() in hay:
                found.append({
                    "entity_id": ent["id"],
                    "name": ent["id"],
                    "match": name,
                    "source": "registry",
                })
                break
    return found


def extract_assets(entity_ids: list[str], registry: list[dict] | None = None) -> list[str]:
    registry = registry or _load_registry()
    assets: list[str] = []
    for eid in entity_ids:
        for ent in registry:
            if ent["id"] == eid:
                for aid in ent.get("asset_ids", []):
                    if aid not in assets:
                        assets.append(aid)
    return assets


def enrich_article(article: dict, voxel_countries: dict[str, dict] | None = None) -> dict:
    registry = _load_registry()
    voxel_countries = voxel_countries or _load_voxel_countries()
    title = article.get("title", "")
    summary = article.get("summary", "")
    text = f"{title} {summary}"

    entities = extract_entities_from_text(title, summary, registry)
    entity_ids = [e["entity_id"] for e in entities]
    geography = extract_geography(title, summary, entity_ids, registry, voxel_countries)
    amounts = extract_amounts(text)
    technologies = extract_technologies(text)
    assets = extract_assets(entity_ids, registry)

    enriched = dict(article)
    enriched["extracted"] = {
        "entities": entities,
        "entity_ids": entity_ids,
        "geography": geography,
        "amounts": amounts,
        "technologies": technologies,
        "assets": assets,
    }
    return enriched
