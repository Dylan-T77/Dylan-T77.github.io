#!/usr/bin/env python3
"""Generate The Tech Briefing static information network from data/network.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "network.json"
XENO_MAIN = ROOT / "scripts" / "xeno_signal_main.html"


def e(value) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def load() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def index_by(items: list[dict], key: str = "id") -> dict:
    return {item[key]: item for item in items}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def page_file(route: str) -> Path:
    route = route.rstrip("/") or ""
    if route == "":
        return ROOT / "index.html"
    if route.endswith(".html"):
        return ROOT / route.lstrip("/")
    return ROOT / route.lstrip("/") / "index.html"


def pretty_date(value: str | None) -> str:
    if not value:
        return "undated"
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d %b %Y").upper()
    except ValueError:
        return value


def nav_items(active: str) -> list[tuple[str, str, str]]:
    return [
        ("/briefings/", "BRIEFINGS", "briefings"),
        ("/signals/", "SIGNALS", "signals"),
        ("/topics/", "TOPICS", "topics"),
        ("/archive/", "ARCHIVE", "archive"),
        ("/lab/", "LAB", "lab"),
        ("/search/", "SEARCH", "search"),
    ]


def current_attr(active: str, key: str) -> str:
    return ' aria-current="page"' if active == key else ""


def render_nav(site: dict, active: str) -> str:
    primary = "".join(
        f'<a href="{e(href)}"{current_attr(active, key)}>{e(label)}</a>'
        for href, label, key in nav_items(active)
    )
    about_current = current_attr(active, "about")
    mobile = primary + f'<a href="/about/"{about_current}>ABOUT</a>'
    return f"""<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
<nav class="nav container" aria-label="Primary">
  <a class="brand-lockup" href="/">
    <span class="brand-name"><span class="status-dot"></span>{e(site["name"])}</span>
    <span class="brand-loop">READ → UNDERSTAND → VERIFY → CONNECT → DISCOVER</span>
  </a>
  <button class="mobile-menu-toggle" id="mobile-menu-toggle" type="button" aria-label="Open navigation" aria-expanded="false" aria-controls="mobile-menu">MENU <span>☰</span></button>
  <div class="nav-cluster">
    <div class="nav-primary">{primary}</div>
    <div class="nav-secondary"><a href="/about/"{about_current}>ABOUT</a></div>
  </div>
  <div class="mobile-menu" id="mobile-menu">{mobile}</div>
</nav>
</header>"""


def breadcrumbs(items: list[tuple[str, str]]) -> str:
    parts = []
    for i, (href, label) in enumerate(items):
        last = i == len(items) - 1
        if last:
            parts.append(f'<span aria-current="page">{e(label)}</span>')
        else:
            parts.append(f'<a href="{e(href)}">{e(label)}</a><span aria-hidden="true">/</span>')
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb">{"".join(parts)}</nav>'


def json_ld(blocks: list[dict]) -> str:
    return "\n".join(
        f'<script type="application/ld+json">{json.dumps(block, ensure_ascii=False)}</script>'
        for block in blocks
    )


def crumb_ld(site: dict, items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": label,
                "item": site["url"] + href,
            }
            for i, (href, label) in enumerate(items)
        ],
    }


def layout(
    data: dict,
    *,
    title: str,
    description: str,
    route: str,
    active: str,
    body: str,
    crumbs: list[tuple[str, str]],
    extra_css: list[str] | None = None,
    extra_js: list[str] | None = None,
    ld: list[dict] | None = None,
    og_type: str = "website",
    article: dict | None = None,
    extra_head: str = "",
) -> str:
    site = data["site"]
    canonical = site["url"] + (route if route != "/" else "/")
    css_links = [
        "/css/style.css",
        "/css/enhancements.css",
        "/css/network.css",
        *(extra_css or []),
    ]
    js_links = ["/js/site.js", *(extra_js or [])]
    edition = site["edition"]
    meta_article = ""
    if article:
        meta_article = f"""
<meta property="article:published_time" content="{e(article.get("published"))}">
<meta property="article:modified_time" content="{e(article.get("updated") or article.get("published"))}">
<meta property="article:author" content="{e(site["author"]["name"])}">"""
        for topic in article.get("topics", []):
            meta_article += f'\n<meta property="article:tag" content="{e(topic)}">'
    ld_blocks = ld or []
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<link rel="alternate" type="application/atom+xml" title="{e(site["name"])} feed" href="/feed.xml">
<meta name="robots" content="index,follow">
<meta property="og:site_name" content="{e(site["name"])}">
<meta property="og:type" content="{e(og_type)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
{meta_article}
{"".join(f'<link rel="stylesheet" href="{e(href)}">' for href in css_links)}
{extra_head}
{json_ld(ld_blocks)}
</head>
<body>
<div class="scanlines" aria-hidden="true"></div>
{render_nav(site, active)}
<div class="edition-strip">
  <div class="container">
    <span>{e(edition["label"])} // <b>{e(edition["status"])}</b></span>
    <span>{e(pretty_date(edition["date"]))} // {e(site["location"]).upper()}</span>
  </div>
</div>
<main id="main">
{body}
</main>
<footer class="site-footer container">
  <span>© {datetime.now().year} {e(site["name"])} // LAB: {e(site["author"]["name"]).upper()}</span>
  <span><a href="/about/">METHODOLOGY</a> · <a href="/feed.xml">FEED</a> · <a href="/lab/">LAB</a></span>
</footer>
{"".join(f'<script src="{e(href)}"></script>' for href in js_links)}
</body>
</html>
"""


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


def homepage(data: dict) -> str:
    site = data["site"]
    briefings = index_by(data["briefings"], "slug")
    lead = briefings[site["edition"]["lead_briefing"]]
    topics = {t["id"]: t for t in data["topics"]}
    entities = {t["id"]: t for t in data["entities"]}
    signals = sorted(data["signals"], key=lambda s: s["published"], reverse=True)
    lab_projects = data["lab"]["projects"][:2]
    crumb = [("/", "Home")]
    body = f"""
<section class="masthead container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">INFORMATION NETWORK // STATIC-FIRST</p>
  <h1>THE<br><span>TECH BRIEFING.</span></h1>
  <p class="masthead-deck">{e(site["tagline"])}</p>
  <div class="loop-row">{' <span>→</span> '.join(e(step) for step in site["loop"])}</div>
</section>
<section class="ed-section container" id="edition">
  <p class="ed-label">02 / CURRENT EDITION</p>
  <div class="lead-meta">{e(site["edition"]["label"])} · {e(pretty_date(site["edition"]["date"]))} · STATUS {e(site["edition"]["status"])}</div>
</section>
<section class="ed-section container" id="lead">
  <p class="ed-label">03 / LEAD BRIEFING</p>
  <div class="lead">
    <div>
      <p class="lead-kicker">{e(lead.get("kicker", "LEAD"))}</p>
      <h2><a href="/briefings/{e(lead["slug"])}/">{e(lead["title"])}</a></h2>
      <p class="lead-deck">{e(lead["deck"])}</p>
    </div>
    <dl class="meta-col">
      <dt>PUBLISHED</dt><dd>{e(pretty_date(lead["published"]))}</dd>
      <dt>STATUS</dt><dd>{e(lead["status"])}</dd>
      <dt>TOPICS</dt><dd>{", ".join(e(topics[t]["name"]) for t in lead["topics"] if t in topics)}</dd>
      <dt>VERIFY</dt><dd><a href="/briefings/{e(lead["slug"])}/#sources">Primary + independent sources</a></dd>
    </dl>
  </div>
</section>
<section class="ed-section container" id="signals">
  <p class="ed-label">04 / CURRENT SIGNALS</p>
  <div class="row-list">
    {"".join(row(f"<b>{e(s['status'])}</b><br>{e(pretty_date(s['published']))}", s["title"], f"/signals/{s['slug']}/", s["deck"]) for s in signals)}
  </div>
</section>
<section class="ed-section container" id="why">
  <p class="ed-label">05 / WHY THIS MATTERS</p>
  {numbered(lead["why_it_matters"][:4])}
</section>
<section class="ed-section container" id="topics">
  <p class="ed-label">06 / TOPIC PULSE</p>
  <table class="pulse-table">
    <thead><tr><th>TOPIC</th><th>STATUS</th><th>NOW</th></tr></thead>
    <tbody>
      {"".join(f'<tr><td><a href="/topics/{e(t["slug"])}/">{e(t["name"])}</a></td><td class="status">{e(t["status"])}</td><td><p>{e(t["current_status"])}</p></td></tr>' for t in data["topics"])}
    </tbody>
  </table>
</section>
<section class="ed-section container" id="timeline">
  <p class="ed-label">07 / DEVELOPING STORY</p>
  <ul class="timeline">
    {"".join(f'<li><time datetime="{e(ev["date"])}">{e(ev["date"])}</time><strong>{e(ev["label"])}</strong><p>{e(ev["text"])}</p></li>' for ev in lead["timeline"])}
  </ul>
</section>
<section class="ed-section container" id="connected">
  <p class="ed-label">08 / CONNECTED INFORMATION</p>
  <div class="connected-grid">
    <div>
      <h3>ENTITIES</h3>
      <ul>{"".join(f'<li><a href="/entities/{e(entities[i]["slug"])}/">{e(entities[i]["name"])}</a></li>' for i in lead["entities"] if i in entities)}</ul>
    </div>
    <div>
      <h3>COLLECTION</h3>
      <ul>{"".join(f'<li><a href="/collections/{e(c["slug"])}/">{e(c["name"])}</a></li>' for c in data["collections"])}</ul>
    </div>
    <div>
      <h3>SOURCES</h3>
      <ul>{"".join(f'<li><a href="{e(s["url"])}" rel="noopener noreferrer">{e(s["title"])}</a></li>' for s in lead["sources"])}</ul>
    </div>
  </div>
</section>
<section class="ed-section container" id="lab">
  <p class="ed-label">09 / LATEST FROM THE LAB</p>
  <div class="row-list">
    {"".join(row(f"<b>{e(p['code'])}</b><br>{e(p['status'])}", p["title"], "/lab/projects/", p["summary"], "LAB") for p in lab_projects)}
  </div>
  <p class="lead-meta" style="margin-top:18px"><a href="/lab/">Open the Lab layer</a> · <a href="/lab/experiments/xeno-signal/">Xeno Signal experiment</a></p>
</section>
<section class="ed-section container" id="method">
  <p class="ed-label">10 / SOURCES AND METHOD</p>
  <div class="method-block">
    <div>
      <p>RSS is an inbox, not the product. Headlines are ingested, normalized, validated, and held at editorial_state=INBOX with publish=false until a briefing or signal is written against primary sources.</p>
      <p>This edition’s lead briefing is sourced to Anthropic’s 27 August 2026 announcement plus independent reports from Ars Technica and CNBC. Partner anecdotes that exist only in the vendor post are labeled REPORTED, not VERIFIED.</p>
    </div>
    <div class="pipeline">{' <span>→</span> '.join(e(step) for step in site["pipeline"])}</div>
  </div>
</section>
"""
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": site["name"],
            "url": site["url"],
            "description": site["description"],
            "potentialAction": {
                "@type": "SearchAction",
                "target": site["url"] + "/search/?q={query}",
                "query-input": "required name=query",
            },
        },
        crumb_ld(site, crumb),
    ]
    return layout(
        data,
        title=f'{site["name"]} — {site["tagline"]}',
        description=site["description"],
        route="/",
        active="home",
        body=body,
        crumbs=crumb,
        ld=ld,
    )


def briefings_index(data: dict) -> str:
    crumb = [("/", "Home"), ("/briefings/", "Briefings")]
    rows = "".join(
        row(
            f"<b>{e(b['status'])}</b><br>{e(pretty_date(b['published']))}",
            b["title"],
            f"/briefings/{b['slug']}/",
            b["deck"],
        )
        for b in sorted(data["briefings"], key=lambda x: x["published"], reverse=True)
    )
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">UNDERSTAND</p>
  <h1>BRIEFINGS<span>.</span></h1>
  <p>Authored, sourced explainers. A briefing is not a headline and not an RSS item. It has to survive VERIFY.</p>
</section>
<section class="ed-section container"><div class="row-list">{rows}</div></section>
"""
    return layout(
        data,
        title="Briefings — The Tech Briefing",
        description="Authored briefings from The Tech Briefing information network.",
        route="/briefings/",
        active="briefings",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def briefing_page(data: dict, briefing: dict) -> str:
    topics = index_by(data["topics"])
    entities = index_by(data["entities"])
    signals = index_by(data["signals"])
    crumb = [("/", "Home"), ("/briefings/", "Briefings"), (f"/briefings/{briefing['slug']}/", briefing["title"])]
    history = briefing.get("history") or []
    related_sigs = [signals[i] for i in briefing.get("related_signals", []) if i in signals]
    watch = "".join(
        f"<li><b>→</b><span><strong>{e(w['item'])}</strong> {e(w['why'])}</span></li>"
        for w in briefing.get("watch_next", [])
    )
    body = f"""
<article class="container article-head">
  {breadcrumbs(crumb)}
  <p class="lead-kicker">{e(briefing.get("kicker", "BRIEFING"))}</p>
  <h1>{e(briefing["title"])}</h1>
  <p class="article-deck">{e(briefing["deck"])}</p>
  <div class="article-byline">
    <span>PUBLISHED <b>{e(pretty_date(briefing["published"]))}</b></span>
    <span>UPDATED <b>{e(pretty_date(briefing.get("updated")))}</b></span>
    <span>STATUS <b>{e(briefing["status"])}</b></span>
  </div>
</article>
<div class="container briefing-layout">
  <div class="briefing-body">
    <h2 id="takeaways">Key takeaways</h2>
    {numbered(briefing["takeaways"])}
    <h2 id="happened">What happened</h2>
    {numbered(briefing["what_happened"])}
    <h2 id="why">Why it matters</h2>
    {numbered(briefing["why_it_matters"])}
    <h2 id="context">Context</h2>
    {numbered(briefing["context"])}
    <h2 id="timeline">Timeline</h2>
    <ul class="timeline">{"".join(f'<li><time datetime="{e(ev["date"])}">{e(ev["date"])}</time><strong>{e(ev["label"])}</strong><p>{e(ev["text"])}</p></li>' for ev in briefing["timeline"])}</ul>
    <h2 id="map">Entities, topics, sources</h2>
    <p>Topics {chips("topics", briefing["topics"], topics)}</p>
    <p>Entities {chips("entities", briefing["entities"], entities)}</p>
    <div id="sources">{source_rows(data, briefing["sources"])}</div>
    <h2 id="related">Related signals</h2>
    <div class="row-list">{"".join(row(f"<b>{e(s['status'])}</b><br>{e(pretty_date(s['published']))}", s["title"], f"/signals/{s['slug']}/", s["deck"]) for s in related_sigs) or empty("NONE YET", "No related signals attached.")}</div>
    <h2 id="watch">What to watch next</h2>
    <ul class="watch-list">{watch}</ul>
    <h2 id="history">Correction / update history</h2>
    <ul class="timeline">{"".join(f'<li><time datetime="{e(h["date"])}">{e(pretty_date(h["date"]))}</time><strong>{e(h["type"].upper())}</strong><p>{e(h["text"])}</p></li>' for h in history) or "<li><p>No corrections issued.</p></li>"}</ul>
  </div>
  <aside class="rail" aria-label="Briefing metadata">
    <h2>RECORD</h2>
    <ul>
      <li>ID {e(briefing["id"])}</li>
      <li>{e(briefing["status"])}</li>
      <li>Edition {e(data["site"]["edition"]["id"])}</li>
    </ul>
    <h2>ON THIS PAGE</h2>
    <ul>
      <li><a href="#takeaways">Takeaways</a></li>
      <li><a href="#happened">What happened</a></li>
      <li><a href="#why">Why it matters</a></li>
      <li><a href="#context">Context</a></li>
      <li><a href="#timeline">Timeline</a></li>
      <li><a href="#sources">Sources</a></li>
      <li><a href="#watch">Watch next</a></li>
    </ul>
    <h2>COLLECTION</h2>
    <ul>{"".join(f'<li><a href="/collections/{e(c)}/">{e(c)}</a></li>' for c in briefing.get("related_collections", []))}</ul>
  </aside>
</div>
"""
    article_ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": briefing["title"],
        "description": briefing["deck"],
        "datePublished": briefing["published"],
        "dateModified": briefing.get("updated") or briefing["published"],
        "mainEntityOfPage": data["site"]["url"] + f"/briefings/{briefing['slug']}/",
        "author": {"@type": "Person", "name": data["site"]["author"]["name"]},
        "publisher": {"@type": "Organization", "name": data["site"]["name"], "url": data["site"]["url"]},
    }
    return layout(
        data,
        title=f'{briefing["title"]} — The Tech Briefing',
        description=briefing["deck"],
        route=f"/briefings/{briefing['slug']}/",
        active="briefings",
        body=body,
        crumbs=crumb,
        og_type="article",
        article=briefing,
        ld=[article_ld, crumb_ld(data["site"], crumb)],
    )


def signals_index(data: dict) -> str:
    crumb = [("/", "Home"), ("/signals/", "Signals")]
    rows = "".join(
        row(
            f"<b>{e(s['status'])}</b><br>{e(pretty_date(s['published']))}",
            s["title"],
            f"/signals/{s['slug']}/",
            s["deck"],
        )
        for s in sorted(data["signals"], key=lambda x: x["published"], reverse=True)
    )
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">READ</p>
  <h1>SIGNALS<span>.</span></h1>
  <p>Curated, source-backed observations. The RSS inbox is not shown here. Ingested headlines stay unpublished until editorial review.</p>
</section>
<section class="ed-section container"><div class="row-list">{rows}</div></section>
"""
    return layout(
        data,
        title="Signals — The Tech Briefing",
        description="Curated signals from The Tech Briefing. RSS ingest is not auto-published.",
        route="/signals/",
        active="signals",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def signal_page(data: dict, signal: dict) -> str:
    topics = index_by(data["topics"])
    entities = index_by(data["entities"])
    briefings = index_by(data["briefings"])
    crumb = [("/", "Home"), ("/signals/", "Signals"), (f"/signals/{signal['slug']}/", signal["title"])]
    related_brief = [briefings[i] for i in signal.get("related_briefings", []) if i in briefings]
    body = f"""
<article class="container article-head">
  {breadcrumbs(crumb)}
  <p class="lead-kicker">SIGNAL // {e(signal["importance"])}</p>
  <h1>{e(signal["title"])}</h1>
  <p class="article-deck">{e(signal["deck"])}</p>
  <div class="article-byline">
    <span>PUBLISHED <b>{e(pretty_date(signal["published"]))}</b></span>
    <span>STATUS <b>{e(signal["status"])}</b></span>
  </div>
</article>
<section class="container briefing-layout">
  <div class="briefing-body">
    <h2>Summary</h2>
    <p>{e(signal["summary"])}</p>
    <h2>Read</h2>
    <p>{e(signal["body"])}</p>
    <h2>Topics and entities</h2>
    {chips("topics", signal["topics"], topics)}
    {chips("entities", signal["entities"], entities)}
    <h2 id="sources">Sources</h2>
    {source_rows(data, signal["sources"])}
    <h2>Related briefings</h2>
    <div class="row-list">{"".join(row(e(pretty_date(b["published"])), b["title"], f"/briefings/{b['slug']}/", b["deck"]) for b in related_brief) or empty("NONE", "No briefing attached yet.")}</div>
  </div>
  <aside class="rail">
    <h2>RECORD</h2>
    <ul>
      <li>ID {e(signal["id"])}</li>
      <li>{e(signal["status"])}</li>
      <li>{e(signal["importance"])}</li>
    </ul>
  </aside>
</section>
"""
    return layout(
        data,
        title=f'{signal["title"]} — The Tech Briefing',
        description=signal["deck"],
        route=f"/signals/{signal['slug']}/",
        active="signals",
        body=body,
        crumbs=crumb,
        og_type="article",
        article=signal,
        ld=[crumb_ld(data["site"], crumb)],
    )


def topics_index(data: dict) -> str:
    crumb = [("/", "Home"), ("/topics/", "Topics")]
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">CONNECT</p>
  <h1>TOPICS<span>.</span></h1>
  <p>Persistent subjects, not tags. Empty coverage is shown honestly.</p>
</section>
<section class="ed-section container">
  <table class="pulse-table">
    <thead><tr><th>TOPIC</th><th>STATUS</th><th>NOW</th></tr></thead>
    <tbody>{"".join(f'<tr><td><a href="/topics/{e(t["slug"])}/">{e(t["name"])}</a></td><td class="status">{e(t["status"])}</td><td><p>{e(t["current_status"])}</p></td></tr>' for t in data["topics"])}</tbody>
  </table>
</section>
"""
    return layout(
        data,
        title="Topics — The Tech Briefing",
        description="Persistent topic pages for The Tech Briefing information network.",
        route="/topics/",
        active="topics",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def topic_page(data: dict, topic: dict) -> str:
    crumb = [("/", "Home"), ("/topics/", "Topics"), (f"/topics/{topic['slug']}/", topic["name"])]
    sigs = [s for s in data["signals"] if topic["id"] in s.get("topics", [])]
    briefs = [b for b in data["briefings"] if topic["id"] in b.get("topics", [])]
    ents = []
    for item in sigs + briefs:
        for entity_id in item.get("entities", []):
            if entity_id not in ents:
                ents.append(entity_id)
    entities = index_by(data["entities"])
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">TOPIC // {e(topic["status"])}</p>
  <h1>{e(topic["name"].upper())}<span>.</span></h1>
  <p>{e(topic["summary"])}</p>
</section>
<section class="ed-section container">
  <p class="ed-label">CURRENT STATUS</p>
  <p>{e(topic["current_status"])}</p>
</section>
<section class="ed-section container">
  <p class="ed-label">LATEST SIGNALS</p>
  {('<div class="row-list">' + ''.join(row(f"<b>{e(s['status'])}</b><br>{e(pretty_date(s['published']))}", s['title'], f"/signals/{s['slug']}/", s['deck']) for s in sigs) + '</div>') if sigs else empty("NO SIGNALS YET", "This topic is being watched. Ingested RSS items are not shown until they pass editorial review.")}
</section>
<section class="ed-section container">
  <p class="ed-label">LATEST BRIEFINGS</p>
  {('<div class="row-list">' + ''.join(row(e(pretty_date(b["published"])), b["title"], f"/briefings/{b['slug']}/", b["deck"]) for b in briefs) + '</div>') if briefs else empty("NO BRIEFING YET", "Coverage is still building. A topic page without a briefing is intentional, not a missing template.")}
</section>
<section class="ed-section container">
  <p class="ed-label">ENTITIES</p>
  {chips("entities", ents, entities) or empty("NONE LINKED", "No published records attach an entity to this topic yet.")}
</section>
<section class="ed-section container">
  <p class="ed-label">WATCH</p>
  {numbered(topic.get("watch", []))}
</section>
"""
    return layout(
        data,
        title=f'{topic["name"]} — The Tech Briefing',
        description=topic["summary"],
        route=f"/topics/{topic['slug']}/",
        active="topics",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def entities_index(data: dict) -> str:
    crumb = [("/", "Home"), ("/entities/", "Entities")]
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">CONNECT</p>
  <h1>ENTITIES<span>.</span></h1>
  <p>Companies, institutions, and standards that records attach to. An entity page can exist before a briefing does.</p>
</section>
<section class="ed-section container">
  <div class="row-list">{"".join(row(f"<b>{e(ent['type'])}</b><br>{e(ent['status'])}", ent["name"], f"/entities/{ent['slug']}/", ent["summary"]) for ent in data["entities"])}</div>
</section>
"""
    return layout(
        data,
        title="Entities — The Tech Briefing",
        description="Entity index for The Tech Briefing information network.",
        route="/entities/",
        active="topics",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def entity_page(data: dict, entity: dict) -> str:
    crumb = [("/", "Home"), ("/entities/", "Entities"), (f"/entities/{entity['slug']}/", entity["name"])]
    sigs = [s for s in data["signals"] if entity["id"] in s.get("entities", [])]
    briefs = [b for b in data["briefings"] if entity["id"] in b.get("entities", [])]
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">{e(entity["type"].upper())} // {e(entity["status"])}</p>
  <h1>{e(entity["name"].upper())}<span>.</span></h1>
  <p>{e(entity["summary"])}</p>
</section>
<section class="ed-section container">
  <p class="ed-label">NOTES</p>
  <p>{e(entity.get("notes", ""))}</p>
</section>
<section class="ed-section container">
  <p class="ed-label">SIGNALS</p>
  {('<div class="row-list">' + ''.join(row(e(pretty_date(s["published"])), s["title"], f"/signals/{s["slug"]}/", s["deck"]) for s in sigs) + '</div>') if sigs else empty("NO SIGNALS", "This entity is registered so future coverage can attach. Nothing authored yet.")}
</section>
<section class="ed-section container">
  <p class="ed-label">BRIEFINGS</p>
  {('<div class="row-list">' + ''.join(row(e(pretty_date(b["published"])), b["title"], f"/briefings/{b["slug"]}/", b["deck"]) for b in briefs) + '</div>') if briefs else empty("NO BRIEFING", "Honest empty state: the architecture is here; the reporting is not.")}
</section>
"""
    return layout(
        data,
        title=f'{entity["name"]} — The Tech Briefing',
        description=entity["summary"],
        route=f"/entities/{entity['slug']}/",
        active="topics",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def collection_page(data: dict, collection: dict) -> str:
    crumb = [("/", "Home"), (f"/collections/{collection['slug']}/", collection["name"])]
    briefings = index_by(data["briefings"])
    signals = index_by(data["signals"])
    topics = index_by(data["topics"])
    entities = index_by(data["entities"])
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">COLLECTION // {e(collection["status"])}</p>
  <h1>{e(collection["name"].upper())}<span>.</span></h1>
  <p>{e(collection["summary"])}</p>
</section>
<section class="ed-section container">
  <p class="ed-label">BRIEFINGS</p>
  <div class="row-list">{"".join(row(e(pretty_date(briefings[i]["published"])), briefings[i]["title"], f"/briefings/{briefings[i]["slug"]}/", briefings[i]["deck"]) for i in collection["briefings"] if i in briefings)}</div>
</section>
<section class="ed-section container">
  <p class="ed-label">SIGNALS</p>
  <div class="row-list">{"".join(row(e(pretty_date(signals[i]["published"])), signals[i]["title"], f"/signals/{signals[i]["slug"]}/", signals[i]["deck"]) for i in collection["signals"] if i in signals)}</div>
</section>
<section class="ed-section container">
  <p class="ed-label">ATTACHED</p>
  {chips("topics", collection["topics"], topics)}
  {chips("entities", collection["entities"], entities)}
  <p>{e(collection.get("notes", ""))}</p>
</section>
"""
    return layout(
        data,
        title=f'{collection["name"]} — The Tech Briefing',
        description=collection["summary"],
        route=f"/collections/{collection['slug']}/",
        active="archive",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def archive_page(data: dict) -> str:
    crumb = [("/", "Home"), ("/archive/", "Archive")]
    items = []
    for briefing in data["briefings"]:
        items.append((briefing["published"], "BRIEFING", briefing["title"], f"/briefings/{briefing['slug']}/", briefing["deck"]))
    for signal in data["signals"]:
        items.append((signal["published"], "SIGNAL", signal["title"], f"/signals/{signal['slug']}/", signal["deck"]))
    items.sort(key=lambda x: x[0], reverse=True)
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">VERIFY / DISCOVER</p>
  <h1>ARCHIVE<span>.</span></h1>
  <p>Published records only. Inbox items never appear here.</p>
</section>
<section class="ed-section container">
  <div class="row-list">{"".join(row(f"<b>{e(kind)}</b><br>{e(pretty_date(date))}", title, href, summary) for date, kind, title, href, summary in items)}</div>
</section>
"""
    return layout(
        data,
        title="Archive — The Tech Briefing",
        description="Published briefings and signals, newest first.",
        route="/archive/",
        active="archive",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def search_page(data: dict, index_items: list[dict]) -> str:
    crumb = [("/", "Home"), ("/search/", "Search")]
    topics = "".join(f'<option value="{e(t["id"])}">{e(t["name"])}</option>' for t in data["topics"])
    sources = "".join(f'<option value="{e(s["id"])}">{e(s["name"])}</option>' for s in data["sources"])
    years = sorted({str(item.get("date", ""))[:4] for item in index_items if item.get("date")}, reverse=True)
    year_opts = "".join(f'<option value="{e(year)}">{e(year)}</option>' for year in years)
    static_rows = "".join(
        row(f"<b>{e(item['type'])}</b><br>{e(pretty_date(item.get('date')))}", item["title"], item["url"], item.get("summary", ""))
        for item in index_items
    )
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">DISCOVER</p>
  <h1>SEARCH<span>.</span></h1>
  <p>Client-side search over the generated index. The full published record list below remains crawlable without JavaScript.</p>
</section>
<section class="ed-section container search-panel">
  <form id="search-form" method="get" action="/search/">
    <input type="search" name="q" placeholder="Titles, summaries, topics, entities, sources" aria-label="Search query">
    <select name="type" aria-label="Type">
      <option value="">All types</option>
      <option value="briefing">Briefing</option>
      <option value="signal">Signal</option>
      <option value="topic">Topic</option>
      <option value="entity">Entity</option>
      <option value="collection">Collection</option>
      <option value="lab">Lab</option>
    </select>
    <select name="topic" aria-label="Topic"><option value="">All topics</option>{topics}</select>
    <select name="source" aria-label="Source"><option value="">All sources</option>{sources}</select>
    <select name="date" aria-label="Year"><option value="">All dates</option>{year_opts}</select>
    <button type="submit">FILTER</button>
  </form>
  <p class="search-count" id="search-count">{len(index_items)} PUBLISHED RECORDS</p>
  <div id="search-results" class="row-list"></div>
  <div id="search-related" class="related-block"></div>
</section>
<section class="ed-section container" id="search-static">
  <p class="ed-label">PUBLISHED INDEX</p>
  <div class="row-list">{static_rows}</div>
</section>
"""
    return layout(
        data,
        title="Search — The Tech Briefing",
        description="Search published briefings, signals, topics, entities, and lab records.",
        route="/search/",
        active="search",
        body=body,
        crumbs=crumb,
        extra_js=["/js/search.js"],
        ld=[crumb_ld(data["site"], crumb)],
    )


def about_page(data: dict) -> str:
    site = data["site"]
    crumb = [("/", "Home"), ("/about/", "About")]
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">VERIFY</p>
  <h1>ABOUT THE<br><span>NETWORK.</span></h1>
  <p>{e(site["description"])}</p>
</section>
<section class="ed-section container">
  <p class="ed-label">WHAT THIS IS</p>
  <p>The Tech Briefing is an information network organized around READ → UNDERSTAND → VERIFY → CONNECT → DISCOVER. It is not a personal homepage, not a generic news site, and not an AI summary feed.</p>
  <p>The Lab is the retained portfolio of {e(site["author"]["name"])}: systems work, hardware, references, and experiments including Xeno Signal. It is a secondary layer.</p>
</section>
<section class="ed-section container">
  <p class="ed-label">PIPELINE</p>
  <div class="pipeline">{' <span>→</span> '.join(e(step) for step in site["pipeline"])}</div>
  <p>GitHub Actions ingest public RSS into <code>data/ingest/rss-inbox.json</code>. Every ingested record has editorial_state=INBOX and publish=false. Nothing in that file is rendered as a briefing or a signal.</p>
</section>
<section class="ed-section container">
  <p class="ed-label">OBJECTS</p>
  <p>SIGNAL · BRIEFING · TOPIC · ENTITY · SOURCE · COLLECTION. Records live in <code>data/network.json</code>. Pages are generated statically so the important content is crawlable HTML.</p>
</section>
<section class="ed-section container">
  <p class="ed-label">CONNECT</p>
  <p><a href="{e(site["author"]["github"])}">GitHub</a> · <a href="{e(site["author"]["x"])}">X</a> · <a href="/lab/">Lab</a></p>
</section>
"""
    return layout(
        data,
        title="About — The Tech Briefing",
        description="What The Tech Briefing is, how records are sourced, and why RSS is not the product.",
        route="/about/",
        active="about",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(site, crumb)],
    )


def lab_index(data: dict) -> str:
    lab = data["lab"]
    crumb = [("/", "Home"), ("/lab/", "Lab")]
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">LAB LAYER // SECONDARY</p>
  <h1>THE<br><span>LAB.</span></h1>
  <p>{e(lab["tagline"])}</p>
  <div class="lab-nav">
    <a href="/lab/projects/">PROJECTS</a>
    <a href="/lab/systems/">SYSTEMS</a>
    <a href="/lab/reference/">REFERENCE</a>
    <a href="/lab/experiments/">EXPERIMENTS</a>
    <a href="/lab/experiments/xeno-signal/">XENO SIGNAL</a>
  </div>
</section>
<section class="ed-section container">
  <p class="ed-label">ABOUT THE BUILDER</p>
  <h2>{e(lab["about"]["headline"])}</h2>
  {"".join(f"<p>{e(p)}</p>" for p in lab["about"]["paragraphs"])}
</section>
<section class="ed-section container">
  <p class="ed-label">ACTIVE / COMPLETE</p>
  <div class="row-list">{"".join(row(f"<b>{e(p['code'])}</b><br>{e(p['status'])}", p["title"], "/lab/projects/", p["summary"]) for p in lab["projects"][:2])}</div>
</section>
<section class="ed-section container">
  <p class="ed-label">CAPABILITY MATRIX</p>
  <div class="row-list">{"".join(row(f"<b>{e(c['code'])}</b>", c["title"], "/lab/systems/", c["text"]) for c in lab["capabilities"])}</div>
</section>
"""
    return layout(
        data,
        title="Lab — The Tech Briefing",
        description="Portfolio, systems, reference, and experiments. Secondary to the briefing network.",
        route="/lab/",
        active="lab",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def lab_projects(data: dict) -> str:
    crumb = [("/", "Home"), ("/lab/", "Lab"), ("/lab/projects/", "Projects")]
    featured = [p for p in data["lab"]["projects"] if p.get("detail")]
    queued = [p for p in data["lab"]["projects"] if not p.get("detail")]
    feat_html = []
    for project in featured:
        flow = ""
        if project.get("flow"):
            flow = "<div class=\"lab-flow\">" + "<i>→</i>".join(f"<span>{e(step)}</span>" for step in project["flow"]) + "</div>"
        tags = "".join(f"<span>{e(tag)}</span>" for tag in project.get("tags", []))
        feat_html.append(f"""<article class="project featured">
          <div class="project-index">{e(project["code"])}</div>
          <div class="project-main">
            <p class="project-tag">{e(project["status"])}</p>
            <h2>{e(project["title"])}</h2>
            <p>{e(project["detail"])}</p>
            {flow}
            <div class="tags">{tags}</div>
          </div>
          <a class="project-link" href="{e(project["url"])}" rel="noopener noreferrer">OPEN REPOSITORY ↗</a>
        </article>""")
    queued_html = "".join(
        f"""<article class="project placeholder"><div class="mini-icon">{e(p["code"])}</div>
        <p class="project-tag">{e(p["status"])}</p><h3>{e(p["title"])}</h3><p>{e(p["summary"])}</p>
        <a class="project-link" href="{e(p["url"])}" rel="noopener noreferrer">REPOSITORY ↗</a></article>"""
        for p in queued
    )
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">LAB / PROJECTS</p>
  <h1>PROJECTS<span>.</span></h1>
  <p>Real systems work. Queued items are labeled as queued.</p>
  <div class="lab-nav"><a href="/lab/">LAB HOME</a><a href="/lab/systems/">SYSTEMS</a><a href="/lab/reference/">REFERENCE</a></div>
</section>
<section class="section container"><div class="section-label">FEATURED</div><div class="section-content">{"".join(feat_html)}</div></section>
<section class="section container"><div class="section-label">QUEUE</div><div class="section-content"><div class="project-grid">{queued_html}</div></div></section>
"""
    return layout(
        data,
        title="Lab projects — The Tech Briefing",
        description="Windows infrastructure, networking, and queued systems projects.",
        route="/lab/projects/",
        active="lab",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def lab_systems(data: dict) -> str:
    crumb = [("/", "Home"), ("/lab/", "Lab"), ("/lab/systems/", "Systems")]
    cards = []
    for system in data["lab"]["systems"]:
        specs = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in system["specs"].items())
        tags = "".join(f"<span>{e(tag)}</span>" for tag in system["tags"])
        cards.append(f"""<article class="device"><div class="device-top"><span>{e(system["code"])}</span><b>{e(system["status"])}</b></div>
        <h2>{e(system["title"])}</h2><p class="role">{e(system["role"])}</p><dl>{specs}</dl>
        <div class="device-tags">{tags}</div></article>""")
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">LAB / HARDWARE</p>
  <h1>MY<br><span>SYSTEMS.</span></h1>
  <p>The machines used to build, test, learn and experiment.</p>
</section>
<section class="section container"><div class="section-label">ACTIVE SYSTEMS</div>
<div class="section-content"><div class="device-grid">{"".join(cards)}</div></div></section>
"""
    return layout(
        data,
        title="Lab systems — The Tech Briefing",
        description="Hardware and operating systems inventory.",
        route="/lab/systems/",
        active="lab",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def lab_reference(data: dict) -> str:
    crumb = [("/", "Home"), ("/lab/", "Lab"), ("/lab/reference/", "Reference")]
    cards = "".join(
        f'<a class="reference-card" href="{e(item["url"])}" rel="noopener noreferrer"><b>{e(item["code"])} // {e(item["title"].upper())}</b><span>{e(item["summary"])}</span></a>'
        for item in data["lab"]["reference"]
    )
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">LAB / KNOWLEDGE BASE</p>
  <h1>TECHNICAL<br><span>REFERENCE.</span></h1>
  <p>Commands, concepts and troubleshooting notes collected while building real systems.</p>
</section>
<section class="section container"><div class="section-label">REFERENCE INDEX</div>
<div class="section-content"><div class="reference-grid">{cards}</div></div></section>
"""
    return layout(
        data,
        title="Lab reference — The Tech Briefing",
        description="Technical command and troubleshooting library.",
        route="/lab/reference/",
        active="lab",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def lab_experiments(data: dict) -> str:
    crumb = [("/", "Home"), ("/lab/", "Lab"), ("/lab/experiments/", "Experiments")]
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">LAB / EXPERIMENTS</p>
  <h1>EXPERIMENTS<span>.</span></h1>
  <p>Interactive and unfinished work that does not belong in a briefing.</p>
</section>
<section class="ed-section container">
  <div class="row-list">
    {row("<b>XENO</b><br>ACTIVE", "Xeno Signal", "/lab/experiments/xeno-signal/", "Interactive deep-space flight computer. Isolated experiment, preserved from the original site.")}
  </div>
</section>
"""
    return layout(
        data,
        title="Lab experiments — The Tech Briefing",
        description="Lab experiments including Xeno Signal.",
        route="/lab/experiments/",
        active="lab",
        body=body,
        crumbs=crumb,
        ld=[crumb_ld(data["site"], crumb)],
    )


def xeno_page(data: dict) -> str:
    crumb = [
        ("/", "Home"),
        ("/lab/", "Lab"),
        ("/lab/experiments/", "Experiments"),
        ("/lab/experiments/xeno-signal/", "Xeno Signal"),
    ]
    markup = XENO_MAIN.read_text(encoding="utf-8")
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">LAB EXPERIMENT // PRESERVED</p>
  <p>Xeno Signal remains an isolated experiment. It is not part of the briefing network.</p>
</section>
<main class="signal-page container">{markup}</main>
"""
    # nested <main> is invalid; use a div wrapper instead of extra main — the layout already has main
    body = f"""
<section class="container" style="padding-top:28px">{breadcrumbs(crumb)}</section>
<div class="signal-page container">{markup}</div>
"""
    return layout(
        data,
        title="Xeno Signal — Lab experiment",
        description="Xeno Signal interactive deep-space interface. A Lab experiment, not a briefing.",
        route="/lab/experiments/xeno-signal/",
        active="lab",
        body=body,
        crumbs=crumb,
        extra_css=["/css/xeno-signal.css"],
        extra_js=["/js/xeno-signal.js"],
        ld=[crumb_ld(data["site"], crumb)],
    )


def redirect_page(target: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url={e(target)}">
<link rel="canonical" href="https://thetechbriefing.com{e(target)}">
<title>{e(title)}</title>
<script>location.replace({json.dumps(target)});</script>
</head>
<body>
<p>This page moved to <a href="{e(target)}">{e(target)}</a>.</p>
</body>
</html>
"""


def not_found(data: dict) -> str:
    crumb = [("/", "Home")]
    body = f"""
<section class="page-head container">
  {breadcrumbs(crumb)}
  <p class="masthead-kicker">404</p>
  <h1>NO RECORD<span>.</span></h1>
  <p>That path is not in the published network. Try search, briefings, or the lab.</p>
  <div class="lab-nav"><a href="/">HOME</a><a href="/search/">SEARCH</a><a href="/lab/">LAB</a></div>
</section>
"""
    html_out = layout(
        data,
        title="Not found — The Tech Briefing",
        description="No published record at this path.",
        route="/404.html",
        active="home",
        body=body,
        crumbs=crumb,
    )
    return html_out.replace('<meta name="robots" content="index,follow">', '<meta name="robots" content="noindex">')


def search_index(data: dict) -> list[dict]:
    items = []

    def add(record_id, type_, title, summary, body, url, topics=None, entities=None, sources=None, date=None):
        items.append(
            {
                "id": record_id,
                "type": type_,
                "title": title,
                "summary": summary or "",
                "body": body or "",
                "url": url,
                "topics": topics or [],
                "entities": entities or [],
                "sources": [s["id"] if isinstance(s, dict) else s for s in (sources or [])],
                "date": date or "",
            }
        )

    for briefing in data["briefings"]:
        add(
            briefing["id"],
            "briefing",
            briefing["title"],
            briefing["deck"],
            " ".join(briefing.get("takeaways", []) + briefing.get("what_happened", []) + briefing.get("why_it_matters", [])),
            f"/briefings/{briefing['slug']}/",
            briefing.get("topics"),
            briefing.get("entities"),
            briefing.get("sources"),
            briefing.get("published"),
        )
    for signal in data["signals"]:
        add(
            signal["id"],
            "signal",
            signal["title"],
            signal["summary"],
            signal.get("body", ""),
            f"/signals/{signal['slug']}/",
            signal.get("topics"),
            signal.get("entities"),
            signal.get("sources"),
            signal.get("published"),
        )
    for topic in data["topics"]:
        add(topic["id"], "topic", topic["name"], topic["summary"], topic.get("current_status", ""), f"/topics/{topic['slug']}/", [topic["id"]])
    for entity in data["entities"]:
        add(entity["id"], "entity", entity["name"], entity["summary"], entity.get("notes", ""), f"/entities/{entity['slug']}/", [], [entity["id"]])
    for collection in data["collections"]:
        add(collection["id"], "collection", collection["name"], collection["summary"], collection.get("notes", ""), f"/collections/{collection['slug']}/", collection.get("topics"), collection.get("entities"))
    for project in data["lab"]["projects"]:
        add(project["id"], "lab", project["title"], project["summary"], project.get("detail", ""), "/lab/projects/", [], [], [], "")
    add("xeno-signal", "lab", "Xeno Signal", "Interactive deep-space experiment.", "lab experiment flight computer", "/lab/experiments/xeno-signal/")
    return items


def sitemap(data: dict, routes: list[str]) -> str:
    urls = []
    today = data["site"]["edition"]["date"]
    for route in routes:
        loc = data["site"]["url"] + (route if route != "/" else "/")
        urls.append(f"  <url><loc>{e(loc)}</loc><lastmod>{e(today)}</lastmod></url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"


def robots(data: dict) -> str:
    return f"""User-agent: *
Allow: /
Disallow: /data/ingest/

Sitemap: {data["site"]["url"]}/sitemap.xml
"""


def atom_feed(data: dict) -> str:
    site = data["site"]
    entries = []
    for briefing in data["briefings"]:
        url = site["url"] + f"/briefings/{briefing['slug']}/"
        entries.append((briefing["published"], briefing["id"], briefing["title"], briefing["deck"], url, "briefing"))
    for signal in data["signals"]:
        url = site["url"] + f"/signals/{signal['slug']}/"
        entries.append((signal["published"], signal["id"], signal["title"], signal["deck"], url, "signal"))
    entries.sort(key=lambda x: x[0], reverse=True)
    xml_entries = []
    for published, record_id, title, deck, url, kind in entries:
        xml_entries.append(
            f"""  <entry>
    <id>tag:thetechbriefing.com,{e(published)}:{e(record_id)}</id>
    <title>{e(title)}</title>
    <link href="{e(url)}" rel="alternate"/>
    <published>{e(published)}T00:00:00Z</published>
    <updated>{e(published)}T00:00:00Z</updated>
    <category term="{e(kind)}"/>
    <summary>{e(deck)}</summary>
  </entry>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{e(site["name"])}</title>
  <subtitle>{e(site["tagline"])}</subtitle>
  <link href="{e(site["url"])}/feed.xml" rel="self"/>
  <link href="{e(site["url"])}/"/>
  <updated>{e(site["edition"]["date"])}T00:00:00Z</updated>
  <id>{e(site["url"])}/</id>
  <author><name>{e(site["author"]["name"])}</name></author>
{chr(10).join(xml_entries)}
</feed>
"""


def main() -> None:
    data = load()
    routes: list[str] = []

    pages = {
        "/": homepage(data),
        "/briefings/": briefings_index(data),
        "/signals/": signals_index(data),
        "/topics/": topics_index(data),
        "/entities/": entities_index(data),
        "/archive/": archive_page(data),
        "/about/": about_page(data),
        "/lab/": lab_index(data),
        "/lab/projects/": lab_projects(data),
        "/lab/systems/": lab_systems(data),
        "/lab/reference/": lab_reference(data),
        "/lab/experiments/": lab_experiments(data),
        "/lab/experiments/xeno-signal/": xeno_page(data),
    }
    for briefing in data["briefings"]:
        pages[f"/briefings/{briefing['slug']}/"] = briefing_page(data, briefing)
    for signal in data["signals"]:
        pages[f"/signals/{signal['slug']}/"] = signal_page(data, signal)
    for topic in data["topics"]:
        pages[f"/topics/{topic['slug']}/"] = topic_page(data, topic)
    for entity in data["entities"]:
        pages[f"/entities/{entity['slug']}/"] = entity_page(data, entity)
    for collection in data["collections"]:
        pages[f"/collections/{collection['slug']}/"] = collection_page(data, collection)

    index_items = search_index(data)
    pages["/search/"] = search_page(data, index_items)

    for route, html_out in pages.items():
        write(page_file(route), html_out)
        routes.append(route)

    write(ROOT / "404.html", not_found(data))
    write(ROOT / "data" / "search-index.json", json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "items": index_items}, indent=2))
    write(ROOT / "sitemap.xml", sitemap(data, routes))
    write(ROOT / "robots.txt", robots(data))
    write(ROOT / "feed.xml", atom_feed(data))
    write(ROOT / ".nojekyll", "")

    redirects = {
        "tech.html": "/signals/",
        "lab.html": "/lab/",
        "systems.html": "/lab/systems/",
        "reference.html": "/lab/reference/",
        "signal.html": "/lab/experiments/xeno-signal/",
    }
    for filename, target in redirects.items():
        write(ROOT / filename, redirect_page(target, f"Redirecting to {target}"))

    print(f"Wrote {len(pages)} pages, search index ({len(index_items)} items), sitemap, feed, redirects.")


if __name__ == "__main__":
    main()
