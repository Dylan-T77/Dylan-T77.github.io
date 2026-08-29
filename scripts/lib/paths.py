"""Repository paths used by the static site build."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "network.json"
ASSET_MANIFEST_PATH = ROOT / "data" / "asset-manifest.json"
XENO_MAIN = ROOT / "scripts" / "xeno_signal_main.html"
RSS_INBOX_PATH = ROOT / "data" / "ingest" / "rss-inbox.json"
