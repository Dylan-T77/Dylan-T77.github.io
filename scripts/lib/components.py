"""Reusable HTML fragments for editorial pages."""

from __future__ import annotations

from scripts.lib.html_utils import e, index_by, pretty_date


def numbered(items: list[str]) -> str:
    lis = "".join(
        f"<li><b>{i:02d}</b><span>{e(item)}</span></li>" for i, item in enumerate(items, 1)
    )
    return f'<ol class="takeaway-list">{lis}</ol>'


def row(meta: str, title: str, href: str, summary: str, go: str = "OPEN") -> str:
    return f"""<article class="row-item">
  <div class="row-meta">{meta}</div>
  <div>
    <h3><a href="{e(href)}">{e(title)}</a></h3>
    <p>{e(summary)}</p>
  </div>
  <a class="row-go" href="{e(href)}">{e(go)}</a>
</article>"""


def chips(kind: str, ids: list[str], lookup: dict) -> str:
    if not ids:
        return ""
    links = []
    for item_id in ids:
        item = lookup.get(item_id)
        if not item:
            continue
        href = f"/{kind}/{e(item.get('slug', item_id))}/"
        links.append(f'<a class="chip" href="{href}">{e(item["name"])}</a>')
    return f'<div class="chip-row">{"".join(links)}</div>' if links else ""


def source_rows(data: dict, refs: list[dict]) -> str:
    sources = index_by(data["sources"])
    items = []
    for ref in refs:
        src = sources.get(ref["id"], {"name": ref["id"], "type": "unknown"})
        items.append(
            f'<li><a href="{e(ref["url"])}" rel="noopener noreferrer">{e(ref.get("title") or src["name"])}</a>'
            f' — {e(src["name"])} ({e(src.get("type", "source"))}, {e(pretty_date(ref.get("published")))})</li>'
        )
    return f'<ul class="prose-list">{"".join(items)}</ul>' if items else '<p class="empty-state">No sources attached.</p>'


def empty(title: str, text: str) -> str:
    return f'<div class="empty-state"><strong>{e(title)}</strong>{e(text)}</div>'


def bar_rows(items: list[tuple[str, int, str | None, str]], chart_id: str, key_attr: str) -> str:
    """Static horizontal bars. items: (label, count, href or None, data-key)."""
    top = max([n for _, n, _, _ in items] + [1])
    rows = []
    for label, count, href, key in items:
        pct = round(100 * count / top) if count else 0
        label_html = f'<a href="{e(href)}">{e(label)}</a>' if href else e(label)
        rows.append(
            f'<div class="bar-row" {key_attr}="{e(key)}" role="button" tabindex="0" aria-label="Filter: {e(label)}">'
            f'<span class="bar-label">{label_html}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{pct}%"></span></span>'
            f'<span class="bar-value">{count}</span>'
            f"</div>"
        )
    return f'<div class="bar-chart" id="{e(chart_id)}">{"".join(rows)}</div>'
