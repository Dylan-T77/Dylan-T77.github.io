#!/usr/bin/env python3
"""Bake Natural Earth country boundaries into a static voxel grid for the 3D world map."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.voxel_geo import load_topojson, rasterize_countries

TOPO_PATH = _REPO_ROOT / "data" / "geo" / "countries-110m.json"
VOXEL_WORLD_PATH = _REPO_ROOT / "data" / "geo" / "voxel-world.v1.json"
VOXEL_COUNTRIES_PATH = _REPO_ROOT / "data" / "geo" / "voxel-countries.v1.json"

COLS = 360
ROWS = 180


def main() -> None:
    if not TOPO_PATH.is_file():
        raise SystemExit(f"Missing topology source: {TOPO_PATH}")

    topo = load_topojson(TOPO_PATH)
    grid, countries = rasterize_countries(topo, COLS, ROWS)

    voxels = [{"x": cx, "y": cy, "c": cid} for (cx, cy), cid in sorted(grid.items())]
    world_payload = {
        "version": 1,
        "projection": "equalEarth",
        "cols": COLS,
        "rows": ROWS,
        "voxel_count": len(voxels),
        "country_count": len(countries),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Natural Earth 1:110m via world-atlas@2/countries-110m.json",
        "voxels": voxels,
    }
    countries_payload = {
        "version": 1,
        "generated_at": world_payload["generated_at"],
        "countries": sorted(countries.values(), key=lambda c: c["name"]),
    }

    VOXEL_WORLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    VOXEL_WORLD_PATH.write_text(json.dumps(world_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    VOXEL_COUNTRIES_PATH.write_text(json.dumps(countries_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"Wrote {len(voxels)} voxels across {len(countries)} countries "
        f"({COLS}x{ROWS}) → {VOXEL_WORLD_PATH.name}, {VOXEL_COUNTRIES_PATH.name}"
    )


if __name__ == "__main__":
    main()
