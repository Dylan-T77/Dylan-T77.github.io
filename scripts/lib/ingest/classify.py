"""Topic and entity keyword classification for ingested items."""

from __future__ import annotations

from scripts.lib.ingest.sectors import SECTOR_LABELS, classify_sectors

# Legacy entity keywords aligned with network.json editorial entities
ENTITIES = {
    "anthropic": ["anthropic", "claude", "model hardware standard", " mhs "],
    "nvidia": ["nvidia", "geforce", "cuda", "jetson", "omniverse"],
    "tsmc": ["tsmc", "taiwan semiconductor"],
    "openai": ["openai", "chatgpt", "sora"],
    "model-hardware-standard": ["model hardware standard", " mhs ", "hardware standard"],
}


def classify_text(title: str, summary: str) -> tuple[list[str], list[str], str | None]:
    hay = f" {title} {summary} ".lower()
    sectors, primary = classify_sectors(title, summary)
    entities = [entity for entity, words in ENTITIES.items() if any(word in hay for word in words)]
    return sectors, entities, primary


def primary_sector_label(sector_id: str | None) -> str:
    if not sector_id:
        return "GENERAL"
    return SECTOR_LABELS.get(sector_id, sector_id.replace("_", " ").upper())
