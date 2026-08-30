"""Site chrome: navigation, breadcrumbs, and page layout shell."""

from __future__ import annotations

import json
from datetime import datetime

from scripts.lib import assets
from scripts.lib.html_utils import e, pretty_date


def nav_items(active: str) -> list[tuple[str, str, str]]:
    return [
        ("/briefings/", "BRIEFINGS", "briefings"),
        ("/signals/", "SIGNALS", "signals"),
        ("/intelligence/", "INTELLIGENCE", "intelligence"),
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


def _resolve_asset_hrefs(paths: list[str]) -> list[str]:
    return [assets.url(path) for path in paths]


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
    module_js: list[str] | None = None,
    ld: list[dict] | None = None,
    og_type: str = "website",
    article: dict | None = None,
    extra_head: str = "",
) -> str:
    site = data["site"]
    canonical = site["url"] + (route if route != "/" else "/")
    social_image = site["url"] + "/og-image.png"
    css_links = _resolve_asset_hrefs(
        [
            "/css/style.css",
            "/css/enhancements.css",
            "/css/network.css",
            *(extra_css or []),
        ]
    )
    js_links = _resolve_asset_hrefs(["/js/site.js", *(extra_js or [])])
    module_links = _resolve_asset_hrefs(module_js or [])
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
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="alternate" type="application/atom+xml" title="{e(site["name"])} feed" href="/feed.xml">
<meta name="robots" content="index,follow">
<meta property="og:site_name" content="{e(site["name"])}">
<meta property="og:type" content="{e(og_type)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:image" content="{e(social_image)}">
<meta property="og:url" content="{e(canonical)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{e(social_image)}">
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
{"".join(f'<script type="module" src="{e(href)}"></script>' for href in module_links)}
</body>
</html>
"""
