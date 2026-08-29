"""Fetch and normalize RSS/Atom items into information records."""

from __future__ import annotations

import hashlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from scripts.lib.ingest.classify import classify_text

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


def record_id(canonical: str, title: str) -> str:
    digest = hashlib.sha256(f"{canonical}|{title.lower()}".encode("utf-8")).hexdigest()[:16]
    return f"inbox-{digest}"


def fetch_feed_items(source: dict, *, limit: int = 25) -> list[dict]:
    request = urllib.request.Request(
        source["url"],
        headers={"User-Agent": "TheTechBriefing-Ingest/1.0 (+https://thetechbriefing.com/about/)"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read()
    root = ET.fromstring(payload)
    nodes = root.findall(".//item") or root.findall(f".//{ATOM}entry")
    ingested_at = datetime.now(timezone.utc).isoformat()
    out: list[dict] = []
    for node in nodes[:limit]:
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
        topics, entities = classify_text(title, summary)
        out.append(
            {
                "id": record_id(canonical, title),
                "title": title,
                "summary": summary[:400],
                "canonical_url": canonical,
                "original_url": url,
                "url": url,
                "source": source["name"],
                "source_id": source["source_id"],
                "source_type": source.get("source_type", "rss"),
                "source_category": source.get("category"),
                "source_reliability": source.get("reliability"),
                "published_at": published,
                "ingested_at": ingested_at,
                "suggested_topics": topics,
                "suggested_entities": entities,
                "editorial_state": "INBOX",
                "publish": False,
            }
        )
    return out


def normalize_all(sources: list[dict]) -> tuple[list[dict], list[str]]:
    collected: list[dict] = []
    errors: list[str] = []
    for source in sources:
        try:
            collected.extend(fetch_feed_items(source))
        except Exception as exc:
            errors.append(f"{source['name']}: {exc}")
    return collected, errors
