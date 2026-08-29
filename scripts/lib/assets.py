"""Content-hashed static asset publishing."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.paths import ASSET_MANIFEST_PATH, ROOT

# Source assets copied to fingerprinted filenames at build time.
ASSET_SOURCES: tuple[str, ...] = (
    "css/style.css",
    "css/enhancements.css",
    "css/network.css",
    "css/dashboard.css",
    "css/xeno-signal.css",
    "css/vendor/leaflet.css",
    "js/site.js",
    "js/dashboard.js",
    "js/search.js",
    "js/xeno-signal.js",
    "js/vendor/leaflet.js",
)

HASHED_NAME = re.compile(r"^(.+)\.([0-9a-f]{8})\.(css|js)$")


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:8]


def hashed_path(source_rel: str, digest: str) -> Path:
    path = Path(source_rel)
    return path.with_name(f"{path.stem}.{digest}{path.suffix}")


def public_url(source_rel: str, digest: str) -> str:
    return "/" + str(hashed_path(source_rel, digest)).replace("\\", "/")


def publish_assets(root: Path = ROOT) -> dict[str, str]:
    """Copy source CSS/JS to content-hashed filenames; return logical → public URL map."""
    manifest: dict[str, str] = {}
    active_outputs: set[Path] = set()

    for source_rel in ASSET_SOURCES:
        source = root / source_rel
        if not source.is_file():
            raise FileNotFoundError(f"Missing build asset source: {source_rel}")

        raw = source.read_bytes()
        digest = content_hash(raw)
        output_rel = hashed_path(source_rel, digest)
        output = root / output_rel
        logical_url = "/" + source_rel.replace("\\", "/")

        if not output.exists() or output.read_bytes() != raw:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(raw)

        manifest[logical_url] = public_url(source_rel, digest)
        active_outputs.add(output)

    _prune_stale_hashed_assets(root, active_outputs)
    _write_manifest(manifest)
    return manifest


def _prune_stale_hashed_assets(root: Path, active_outputs: set[Path]) -> None:
    for pattern in ("css/**/*.css", "js/**/*.js"):
        for path in root.glob(pattern):
            if not HASHED_NAME.match(path.name):
                continue
            if path not in active_outputs:
                path.unlink(missing_ok=True)


def _write_manifest(manifest: dict[str, str]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assets": manifest,
    }
    ASSET_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSET_MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def configure(manifest: dict[str, str]) -> None:
    global _MANIFEST
    _MANIFEST = dict(manifest)


def url(logical: str) -> str:
    """Resolve a logical asset path (e.g. /css/style.css) to its hashed public URL."""
    if not logical.startswith("/"):
        logical = "/" + logical
    return _MANIFEST.get(logical, logical)


_MANIFEST: dict[str, str] = {}
