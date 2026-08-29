#!/usr/bin/env python3
"""Run the full editorial ingestion pipeline locally or in CI.

SOURCES → INGEST → NORMALIZE → VALIDATE → DEDUPLICATE → CLASSIFY → EXTRACT EVENTS

Safety invariants:
  - editorial_state = INBOX
  - publish = false
  - one source failure must not block others
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.ingest.dedupe import dedupe_items
from scripts.lib.ingest.extract_events import extract_all_events
from scripts.lib.ingest.normalize import normalize_all
from scripts.lib.ingest.sources import PIPELINE, load_sources
from scripts.lib.ingest.validate import validate_items
from scripts.lib.paths import (
    INTELLIGENCE_ARTICLES_PATH,
    INTELLIGENCE_EVENTS_PATH,
    RSS_INBOX_PATH,
)


def main() -> None:
    sources = load_sources()
    raw_items, ingest_errors = normalize_all(sources)
    valid_items, validation_errors = validate_items(raw_items)
    unique_items = dedupe_items(valid_items)
    events = extract_all_events(unique_items)
    generated_at = datetime.now(timezone.utc).isoformat()

    inbox_payload = {
        "generated_at": generated_at,
        "pipeline": PIPELINE,
        "policy": {
            "auto_publish": False,
            "editorial_state": "INBOX",
            "note": "Inbox records must not be rendered as Tech Briefing briefings or signals.",
        },
        "errors": ingest_errors + validation_errors,
        "items": unique_items,
    }
    RSS_INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    RSS_INBOX_PATH.write_text(json.dumps(inbox_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    articles_payload = {
        "version": 1,
        "generated_at": generated_at,
        "freshness": "moderate",
        "articles": unique_items,
    }
    INTELLIGENCE_ARTICLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    INTELLIGENCE_ARTICLES_PATH.write_text(
        json.dumps(articles_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    events_payload = {
        "version": 1,
        "generated_at": generated_at,
        "freshness": "persistent",
        "events": events,
    }
    INTELLIGENCE_EVENTS_PATH.write_text(
        json.dumps(events_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    published_flags = {item["publish"] for item in unique_items}
    print(f"Wrote {len(unique_items)} inbox records → {RSS_INBOX_PATH}")
    print(f"Wrote {len(events)} extracted events → {INTELLIGENCE_EVENTS_PATH}")
    print("publish flags:", published_flags)
    if True in published_flags:
        raise SystemExit("Invariant violated: inbox item marked publish=true")
    if ingest_errors:
        print("source errors:", len(ingest_errors))


if __name__ == "__main__":
    main()
