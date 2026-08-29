"""Aggregate published network records by country for the voxel world map."""

from __future__ import annotations

from scripts.lib.voxel_geo import resolve_country_id


def country_records(
    *,
    loc_items: list[dict],
    entities: dict,
    signals: list[dict],
    voxel_countries: dict[str, dict],
) -> list[dict]:
    """Roll city-level entity sites up to country-level intelligence records."""
    by_country: dict[str, dict] = {}

    for loc in loc_items:
        cid = resolve_country_id(loc["country"], voxel_countries)
        if not cid:
            continue
        group = by_country.setdefault(
            cid,
            {
                "id": cid,
                "name": voxel_countries[cid]["name"],
                "country_label": loc["country"],
                "entity_ids": [],
                "sites": [],
                "signals": [],
                "briefings": [],
                "topics": [],
                "signal_count": 0,
                "latest": None,
            },
        )
        group["entity_ids"].extend(eid for eid in loc["entity_ids"] if eid not in group["entity_ids"])
        group["sites"].append(
            {
                "id": loc["id"],
                "city": loc["city"],
                "country": loc["country"],
                "name": loc["name"],
                "signal_count": loc["signal_count"],
                "entities": loc["entities"],
            }
        )
        for sid in loc["signals"]:
            if sid not in group["signals"]:
                group["signals"].append(sid)
        for brief in loc["briefings"]:
            if brief["id"] not in {b["id"] for b in group["briefings"]}:
                group["briefings"].append(brief)
        for topic in loc["topics"]:
            if topic not in group["topics"]:
                group["topics"].append(topic)
        if loc.get("latest") and (
            group["latest"] is None or loc["latest"]["published"] > group["latest"]["published"]
        ):
            group["latest"] = loc["latest"]

    signal_index = {s["id"]: s for s in signals}
    out: list[dict] = []
    for cid in sorted(by_country, key=lambda k: by_country[k]["name"]):
        group = by_country[cid]
        group["signal_count"] = len(group["signals"])
        group["entities"] = [
            {
                "id": eid,
                "name": entities[eid]["name"],
                "type": entities[eid]["type"],
                "url": f"/entities/{entities[eid]['slug']}/",
            }
            for eid in group["entity_ids"]
            if eid in entities
        ]
        group["has_entity_presence"] = bool(group["entities"])
        group["has_signals"] = group["signal_count"] > 0
        group["presence"] = (
            "signals" if group["has_signals"] else "entities_only" if group["has_entity_presence"] else "none"
        )
        if group["latest"] is None and group["signals"]:
            latest_id = max(group["signals"], key=lambda sid: signal_index[sid]["published"])
            sig = signal_index[latest_id]
            group["latest"] = {
                "id": sig["id"],
                "title": sig["title"],
                "url": f"/signals/{sig['slug']}/",
                "published": sig["published"],
                "status": sig["status"],
            }
        out.append(group)
    return out


def empty_country_record(cid: str, name: str) -> dict:
    return {
        "id": cid,
        "name": name,
        "country_label": name,
        "entity_ids": [],
        "sites": [],
        "signals": [],
        "briefings": [],
        "topics": [],
        "signal_count": 0,
        "latest": None,
        "entities": [],
        "has_entity_presence": False,
        "has_signals": False,
        "presence": "none",
    }


def world_country_registry(voxel_countries: dict[str, dict]) -> list[dict]:
    """Minimal id/name records for every country in static geometry."""
    return [
        empty_country_record(cid, meta["name"])
        for cid, meta in sorted(voxel_countries.items(), key=lambda kv: kv[1]["name"])
    ]
