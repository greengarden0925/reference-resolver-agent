"""Minimal RSS/Atom feed parser using stdlib only (no feedparser dependency)."""
import logging
import xml.etree.ElementTree as ET
from typing import List

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc":   "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "media": "http://search.yahoo.com/mrss/",
}
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DailyNewsBot/1.0)",
    "Accept": "application/rss+xml, application/atom+xml, text/xml, */*",
}


def _clean(html: str, max_len: int = 350) -> str:
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ").strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def _text(el, tag: str, ns: dict | None = None) -> str:
    child = el.find(tag) if ns is None else el.find(tag, ns)
    return (child.text or "").strip() if child is not None else ""


def parse_feed(url: str, max_items: int = 5, source_name: str = "") -> List[dict]:
    try:
        with httpx.Client(timeout=12, headers=_HEADERS, follow_redirects=True) as c:
            resp = c.get(url)
            resp.raise_for_status()
            content = resp.content
    except Exception as exc:
        logger.warning("Fetch failed [%s]: %s", source_name or url[:60], exc)
        return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        logger.warning("XML parse failed [%s]: %s", source_name, exc)
        return []

    # Strip default namespace from tag names
    tag = root.tag
    is_atom = "atom" in tag.lower() or tag.endswith("}feed")

    items = []
    if is_atom:
        for entry in root.findall("atom:entry", _NS) or root.findall("{http://www.w3.org/2005/Atom}entry"):
            title   = _text(entry, "atom:title", _NS) or _text(entry, "{http://www.w3.org/2005/Atom}title")
            link_el = entry.find("atom:link", _NS) or entry.find("{http://www.w3.org/2005/Atom}link")
            link    = (link_el.get("href", "") if link_el is not None else "")
            summary = (
                _text(entry, "atom:summary", _NS)
                or _text(entry, "{http://www.w3.org/2005/Atom}summary")
                or _text(entry, "atom:content", _NS)
                or _text(entry, "{http://www.w3.org/2005/Atom}content")
            )
            date = (
                _text(entry, "atom:published", _NS)
                or _text(entry, "{http://www.w3.org/2005/Atom}published")
                or _text(entry, "atom:updated", _NS)
            )
            items.append({"title": title, "url": link, "summary": _clean(summary), "published_at": date})
    else:
        # RSS 2.0
        channel = root.find("channel") or root
        for item in (channel.findall("item") or []):
            title   = _text(item, "title")
            link    = _text(item, "link")
            summary = (
                _text(item, "description")
                or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
            )
            date    = _text(item, "pubDate") or _text(item, "{http://purl.org/dc/elements/1.1/}date")
            items.append({"title": title, "url": link, "summary": _clean(summary), "published_at": date})

    results = []
    for it in items[:max_items]:
        results.append({
            "source":       source_name,
            "title":        it["title"].strip(),
            "summary":      it["summary"],
            "url":          it["url"],
            "published_at": it["published_at"],
        })
    return results
