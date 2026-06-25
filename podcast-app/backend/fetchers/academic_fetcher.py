import logging
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import quote

import httpx

import config
from rss_parser import parse_feed, _clean

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DailyNewsBot/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _from_feeds(journal_key: str, default_score: float) -> List[dict]:
    papers: List[dict] = []
    for feed_info in config.ACADEMIC_FEEDS.get(journal_key, []):
        raw = parse_feed(feed_info["url"], max_items=4, source_name=feed_info["name"])
        for item in raw:
            item["authors"] = ""
            item["abstract"] = item.pop("summary", "")
            item["doi"] = ""
            item["relevance_score"] = default_score
            papers.append(item)
    return papers


def fetch_nature_articles() -> List[dict]:
    return _from_feeds("nature", 0.75)


def fetch_nejm_articles() -> List[dict]:
    return _from_feeds("nejm", 0.80)


def fetch_lancet_articles() -> List[dict]:
    return _from_feeds("lancet", 0.75)


def search_pubmed(topics: List[str], max_results: int = 5) -> List[dict]:
    papers: List[dict] = []
    timeout = httpx.Timeout(15.0)

    for topic in topics[:3]:
        try:
            query = f'("{topic}"[Title/Abstract]) AND ("last 14 days"[PDat])'
            search_url = (
                f"{config.PUBMED_BASE_URL}/esearch.fcgi"
                f"?db=pubmed&term={quote(query)}&retmax={max_results}&sort=relevance&retmode=json"
            )
            with httpx.Client(timeout=timeout, headers=_HEADERS) as client:
                resp = client.get(search_url)
                resp.raise_for_status()
                ids = resp.json().get("esearchresult", {}).get("idlist", [])
                if not ids:
                    continue

                fetch_url = (
                    f"{config.PUBMED_BASE_URL}/efetch.fcgi"
                    f"?db=pubmed&id={','.join(ids)}&retmode=xml&rettype=abstract"
                )
                resp2 = client.get(fetch_url)
                resp2.raise_for_status()
                root = ET.fromstring(resp2.content)

                for art in root.findall(".//PubmedArticle"):
                    try:
                        title    = art.findtext(".//ArticleTitle") or ""
                        abstract = art.findtext(".//AbstractText") or ""
                        pmid     = art.findtext(".//PMID") or ""
                        journal  = art.findtext(".//Title") or ""

                        author_nodes = art.findall(".//Author")
                        names = []
                        for a in author_nodes[:3]:
                            last = a.findtext("LastName") or ""
                            fore = a.findtext("ForeName") or ""
                            if last:
                                names.append(f"{last} {fore}".strip())
                        authors = ", ".join(names)
                        if len(author_nodes) > 3:
                            authors += " et al."

                        doi = ""
                        for id_el in art.findall(".//ArticleId"):
                            if id_el.get("IdType") == "doi":
                                doi = id_el.text or ""
                                break

                        year  = art.findtext(".//PubDate/Year") or ""
                        month = art.findtext(".//PubDate/Month") or ""

                        papers.append(
                            {
                                "source":          f"PubMed – {journal[:40]}" if journal else "PubMed",
                                "title":           title.strip(),
                                "authors":         authors,
                                "abstract":        _clean(abstract),
                                "url":             f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                "doi":             doi,
                                "published_at":    f"{year} {month}".strip(),
                                "relevance_score": 0.90,
                            }
                        )
                    except Exception as exc:
                        logger.debug("PubMed parse error: %s", exc)

        except Exception as exc:
            logger.warning("PubMed search failed for '%s': %s", topic, exc)

    return papers[:max_results]


def fetch_all_academic(research_topics: List[str] | None = None) -> List[dict]:
    if research_topics is None:
        research_topics = config.RESEARCH_TOPICS

    logger.info("Fetching Nature articles…")
    papers = fetch_nature_articles()

    logger.info("Fetching NEJM articles…")
    papers += fetch_nejm_articles()

    logger.info("Fetching Lancet articles…")
    papers += fetch_lancet_articles()

    logger.info("Searching PubMed: %s", research_topics[:3])
    papers += search_pubmed(research_topics)

    papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    return papers[: config.MAX_ACADEMIC_PAPERS]
