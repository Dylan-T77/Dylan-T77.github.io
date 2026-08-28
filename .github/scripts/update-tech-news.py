#!/usr/bin/env python3
"""Ingest public RSS into an editorial inbox.

Pipeline stage written by this script:
  SOURCES → INGEST → NORMALIZE → VALIDATE → DEDUPLICATE → CLASSIFY

Items are never published. Every record is written with:
  editorial_state = INBOX
  publish = false

Authored Tech Briefing content lives in data/network.json and is generated
by scripts/build_site.py. This inbox is a feed for human review only.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "ingest" / "rss-inbox.json"

FEEDS = {
    "Ars Technica": {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "source_id": "ars-technica",
        "source_type": "journalism",
    },
    "The Register": {
        "url": "https://www.theregister.com/headlines.atom",
        "source_id": "the-register",
        "source_type": "journalism",
    },
    "WIRED": {
        "url": "https://www.wired.com/feed/rss",
        "source_id": "wired",
        "source_type": "journalism",
    },
    "BleepingComputer": {
        "url": "https://www.bleepingcomputer.com/feed/",
        "source_id": "bleepingcomputer",
        "source_type": "journalism",
    },
    "TechCrunch": {
        "url": "https://techcrunch.com/feed/",
        "source_id": "techcrunch",
        "source_type": "journalism",
    },
    "IEEE Spectrum": {
        "url": "https://spectrum.ieee.org/feeds/feed.rss",
        "source_id": "ieee-spectrum",
        "source_type": "journalism",
    },
    "Hacker News": {
        "url": "https://hnrss.org/frontpage",
        "source_id": "hacker-news",
        "source_type": "aggregator",
    },
}

TOPICS = {
    "ai": ["artificial intelligence", "machine learning", " llm", " ai ", "openai", "anthropic", "gemini", "qwen", "llama", "claude", "model hardware", "agentic"],
    "robotics": ["robot", "robotics", "drone", "autonomous", "humanoid", "lerobot", "robotic arm"],
    "space": ["space", "nasa", "spacex", "rocket", "satellite", "orbit", "moon", "mars", "artemis"],
    "cybersecurity": ["security", "cyber", "vulnerability", "exploit", "malware", "ransomware", "breach", "cve", "phishing", "zero-day"],
    "semiconductors": ["cpu", "gpu", "processor", "chip", "semiconductor", "nvidia", "amd", "intel", "tsmc", "foundry", "wafer"],
}

ENTITIES = {
    "anthropic": ["anthropic", "claude", "model hardware standard", " mhs "],
    "nvidia": ["nvidia", "geforce", "cuda", "jetson", "omniverse"],
    "tsmc": ["tsmc", "taiwan semiconductor"],
    "openai": ["openai", "chatgpt", "sora"],
    "model-hardware-standard": ["model hardware standard", " mhs ", "hardware standard"],
}

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid", "ref"}
    ]
    path = parsed.path or "/"
    return urlunparse(
        (parsed.scheme or "https", parsed.netloc.lower(), path.rstrip("/") or "/", "", urlencode(query), "")
    )


def parse_date(*values: str) -> str | None:
    for raw in values:
        text = clean(raw)
        if not text:
            continue
        try:
            return parsedate_to_datetime(text).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            pass
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(text[:19] if "T" in fmt else text[:10], fmt)
                return dt.replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                continue
    return None


def child_text(node: ET.Element, names: list[str]) -> str:
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return clean(found.text)
    return ""


def link_of(node: ET.Element) -> str:
    text = child_text(node, ["link", f"{ATOM}link"])
    if text:
        return text
    for found in list(node.findall("link")) + list(node.findall(f"{ATOM}link")):
        href = found.attrib.get("href") or found.attrib.get("url")
        if href:
            rel = found.attrib.get("rel", "alternate")
            if rel in {"alternate", ""} or href:
                return href.strip()
    guid = node.find("guid")
    if guid is not None and (guid.attrib.get("isPermaLink", "true").lower() != "false") and guid.text:
        return guid.text.strip()
    return ""


def classify(title: str, summary: str) -> tuple[list[str], list[str]]:
    hay = f" {title} {summary} ".lower()
    topics = [topic for topic, words in TOPICS.items() if any(word in hay for word in words)]
    entities = [entity for entity, words in ENTITIES.items() if any(word in hay for word in words)]
    return topics, entities


def record_id(canonical: str, title: str) -> str:
    digest = hashlib.sha256(f"{canonical}|{title.lower()}".encode("utf-8")).hexdigest()[:16]
    return f"inbox-{digest}"


def feed_items(source_name: str, meta: dict) -> list[dict]:
    request = urllib.request.Request(
        meta["url"],
        headers={"User-Agent": "TheTechBriefing-Ingest/1.0 (+https://thetechbriefing.com/about/)"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read()
    root = ET.fromstring(payload)
    nodes = root.findall(".//item") or root.findall(f".//{ATOM}entry")
    out = []
    for node in nodes[:25]:
        title = child_text(node, ["title", f"{ATOM}title"])
        summary = child_text(
            node,
            ["description", "summary", f"{ATOM}summary", f"{ATOM}content", f"{DC}description"],
        )
        url = link_of(node)
        published = parse_date(
            child_text(node, ["pubDate", "published", f"{ATOM}published", f"{ATOM}updated", f"{DC}date"]),
            node.findtext("pubDate") or "",
            node.findtext(f"{ATOM}published") or "",
            node.findtext(f"{ATOM}updated") or "",
        )
        if not title or not url:
            continue
        canonical = canonical_url(url)
        topics, entities = classify(title, summary)
        out.append(
            {
                "id": record_id(canonical, title),
                "title": title,
                "summary": summary[:400],
                "canonical_url": canonical,
                "url": url,
                "published_at": published,
                "source": source_name,
                "source_id": meta["source_id"],
                "source_type": meta["source_type"],
                "suggested_topics": topics,
                "suggested_entities": entities,
                "editorial_state": "INBOX",
                "publish": False,
            }
        )
    return out


def main() -> None:
    collected: list[dict] = []
    errors: list[str] = []
    for source_name, meta in FEEDS.items():
        try:
            collected.extend(feed_items(source_name, meta))
        except Exception as exc:  # keep ingest resilient; one dead feed must not block others
            errors.append(f"{source_name}: {exc}")
            print("WARN", source_name, exc)

    unique: list[dict] = []
    seen: set[str] = set()
    for item in collected:
        key = item["canonical_url"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": [
            "SOURCES",
            "INGEST",
            "NORMALIZE",
            "VALIDATE",
            "DEDUPLICATE",
            "CLASSIFY",
            "EDITORIAL REVIEW",
            "PUBLISH",
            "CONNECT",
        ],
        "policy": {
            "auto_publish": False,
            "editorial_state": "INBOX",
            "note": "Inbox records must not be rendered as Tech Briefing briefings or signals.",
        },
        "errors": errors,
        "items": unique,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    published_flags = {item["publish"] for item in unique}
    print(f"Wrote {len(unique)} inbox records to {OUT}")
    print("publish flags:", published_flags)
    print("editorial states:", {item["editorial_state"] for item in unique})
    if True in published_flags:
        raise SystemExit("Invariant violated: inbox item marked publish=true")


if __name__ == "__main__":
    main()
