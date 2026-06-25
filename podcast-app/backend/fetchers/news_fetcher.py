import logging
from typing import Dict, List

import config
from rss_parser import parse_feed

logger = logging.getLogger(__name__)


def fetch_category(category: str) -> List[dict]:
    feeds = config.NEWS_FEEDS.get(category, [])
    all_articles: List[dict] = []

    for feed_info in feeds:
        articles = parse_feed(
            feed_info["url"],
            max_items=3,
            source_name=feed_info["name"],
        )
        all_articles.extend(articles)
        if len(all_articles) >= config.MAX_NEWS_PER_CATEGORY:
            break

    return all_articles[: config.MAX_NEWS_PER_CATEGORY]


def fetch_all_news() -> Dict[str, List[dict]]:
    results: Dict[str, List[dict]] = {}
    for category in config.NEWS_FEEDS:
        logger.info("Fetching category: %s", category)
        results[category] = fetch_category(category)
        logger.info("  → %d articles", len(results[category]))
    return results
