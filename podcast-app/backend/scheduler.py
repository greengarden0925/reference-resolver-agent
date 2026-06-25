import asyncio
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config

logger = logging.getLogger(__name__)
_scheduler = AsyncIOScheduler()


async def run_daily_fetch() -> None:
    from datetime import datetime

    import database
    from fetchers.academic_fetcher import fetch_all_academic
    from fetchers.news_fetcher import fetch_all_news
    from podcast_generator import generate_podcast_script

    tz = pytz.timezone(config.TIMEZONE)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    logger.info("Daily fetch started for %s", today)

    try:
        news = fetch_all_news()
        for category, articles in news.items():
            database.save_articles(today, category, articles)

        research_topics = database.get_setting("research_topics", config.RESEARCH_TOPICS)
        papers = fetch_all_academic(research_topics)
        database.save_academic_papers(today, papers)

        script = generate_podcast_script(today, news, papers)
        database.save_digest(today, script)

        logger.info("Daily fetch completed for %s", today)
    except Exception as exc:
        logger.error("Daily fetch failed: %s", exc, exc_info=True)


def start_scheduler() -> None:
    tz = pytz.timezone(config.TIMEZONE)
    trigger = CronTrigger(
        hour=config.DAILY_HOUR,
        minute=config.DAILY_MINUTE,
        timezone=tz,
    )
    _scheduler.add_job(run_daily_fetch, trigger, id="daily_fetch", replace_existing=True)
    _scheduler.start()
    logger.info(
        "Scheduler started: daily fetch at %02d:%02d %s",
        config.DAILY_HOUR,
        config.DAILY_MINUTE,
        config.TIMEZONE,
    )


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
