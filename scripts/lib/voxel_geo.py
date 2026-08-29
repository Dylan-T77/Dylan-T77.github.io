"""TopoJSON decoding and Equal Earth projection for voxel world geometry."""

from __future__ import annotations

import json
import math
from pathlib import Path


def load_topojson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decode_arcs(topo: dict) -> list[list[tuple[float, float]]]:
    scale = topo["transform"]["scale"]
    trans = topo["transform"]["translate"]
    decoded: list[list[tuple[float, float]]] = []
    for arc in topo["arcs"]:
        x = y = 0.0
        pts: list[tuple[float, float]] = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * scale[0] + trans[0], y * scale[1] + trans[1]))
        decoded.append(pts)
    return decoded


def ring_coords(arc_ids: list[int], arcs: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for arc_id in arc_ids:
        rev = arc_id < 0
        idx = ~arc_id if rev else arc_id
        pts = arcs[idx]
        if rev:
            pts = list(reversed(pts))
        if out:
            out.extend(pts[1:])
        else:
            out.extend(pts)
    return out


def geometry_rings(geom: dict, arcs: list[list[tuple[float, float]]]) -> list[list[list[tuple[float, float]]]]:
    if geom["type"] == "Polygon":
        return [[ring_coords(ring, arcs) for ring in geom["arcs"]]]
    if geom["type"] == "MultiPolygon":
        return [[ring_coords(ring, arcs) for ring in poly] for poly in geom["arcs"]]
    return []


def equal_earth(lon: float, lat: float) -> tuple[float, float]:
    a1, a2, a3, a4 = 1.340264, -0.081106, 0.000893, 0.003796
    lam = math.radians(lon)
    phi = math.radians(lat)
    theta = math.asin(math.sqrt(3) / 2 * math.sin(phi))
    t2 = theta * theta
    t6 = t2 * t2 * t2
    denom = math.sqrt(3) / 2 * (a1 + 3 * a2 * t2 + t6 * (7 * a3 + 9 * a4 * t2))
    x = lam * math.cos(theta) / denom
    y = theta * (a1 + a2 * t2 + t6 * (a3 + a4 * t2))
    return x, y


def rasterize_countries(
    topo: dict,
    cols: int,
    rows: int,
) -> tuple[dict[tuple[int, int], str], dict[str, dict]]:
    """Return grid cell → country id, and country id → metadata."""
    arcs = decode_arcs(topo)
    geoms = topo["objects"]["countries"]["geometries"]

    xs: list[float] = []
    ys: list[float] = []
    for lon in range(-180, 181, 5):
        for lat in range(-90, 91, 5):
            x, y = equal_earth(lon, lat)
            xs.append(x)
            ys.append(y)
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    grid: dict[tuple[int, int], str] = {}
    countries: dict[str, dict] = {}

    for geom in geoms:
        cid = str(geom.get("id", ""))
        name = geom["properties"]["name"]
        edges: list[tuple[tuple[float, float], tuple[float, float]]] = []

        for poly in geometry_rings(geom, arcs):
            for ring in poly:
                projected = [equal_earth(lon, lat) for lon, lat in ring]
                grid_pts = [
                    (
                        (px - x0) / (x1 - x0) * cols,
                        (py - y0) / (y1 - y0) * rows,
                    )
                    for px, py in projected
                ]
                for i in range(len(grid_pts)):
                    a, b = grid_pts[i], grid_pts[(i + 1) % len(grid_pts)]
                    if a[1] != b[1]:
                        edges.append((a, b))

        if not edges:
            continue

        ymin = max(0, int(min(min(a[1], b[1]) for a, b in edges)))
        ymax = min(rows - 1, int(max(max(a[1], b[1]) for a, b in edges)) + 1)
        filled = 0

        for cy in range(ymin, ymax + 1):
            scan_y = cy + 0.5
            xints: list[float] = []
            for (ax, ay), (bx, by) in edges:
                if (ay <= scan_y < by) or (by <= scan_y < ay):
                    xints.append(ax + (scan_y - ay) / (by - ay) * (bx - ax))
            xints.sort()
            for k in range(0, len(xints) - 1, 2):
                x_start = max(0, int(math.ceil(xints[k] - 0.5)))
                x_end = min(cols - 1, int(math.floor(xints[k + 1] - 0.5)))
                for cx in range(x_start, x_end + 1):
                    if (cx, cy) not in grid:
                        grid[(cx, cy)] = cid
                        filled += 1

        if filled == 0:
            # Centroid fallback for small island states.
            all_pts = [
                equal_earth(lon, lat)
                for poly in geometry_rings(geom, arcs)
                for ring in poly
                for lon, lat in ring
            ]
            if all_pts:
                cx_f = sum(p[0] for p in all_pts) / len(all_pts)
                cy_f = sum(p[1] for p in all_pts) / len(all_pts)
                cx = int((cx_f - x0) / (x1 - x0) * cols)
                cy = int((cy_f - y0) / (y1 - y0) * rows)
                cx = max(0, min(cols - 1, cx))
                cy = max(0, min(rows - 1, cy))
                grid[(cx, cy)] = cid
                filled = 1

        if filled:
            country_cells = [(cx, cy) for (cx, cy), gid in grid.items() if gid == cid]
            cx_mean = sum(c[0] for c in country_cells) / len(country_cells)
            cy_mean = sum(c[1] for c in country_cells) / len(country_cells)
            countries[cid] = {
                "id": cid,
                "name": name,
                "voxel_count": len(country_cells),
                "centroid": {"x": round(cx_mean, 2), "y": round(cy_mean, 2)},
            }

    return grid, countries


# Entity location country strings → Natural Earth country names.
COUNTRY_ALIASES: dict[str, str] = {
    "United States": "United States of America",
    "USA": "United States of America",
    "US": "United States of America",
    "UK": "United Kingdom",
    "Britain": "United Kingdom",
    "Taiwan": "Taiwan",
    "South Korea": "Korea",
    "Korea, South": "Korea",
    "Russia": "Russia",
}


def resolve_country_id(country_label: str, countries: dict[str, dict]) -> str | None:
    label = COUNTRY_ALIASES.get(country_label, country_label).strip().lower()
    for cid, meta in countries.items():
        if meta["name"].lower() == label:
            return cid
    for cid, meta in countries.items():
        name = meta["name"].lower()
        if label in name or name in label:
            return cid
    return None
