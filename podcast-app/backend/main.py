import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pytz
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import database
from scheduler import run_daily_fetch, start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Daily News Podcast", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.on_event("startup")
async def startup_event() -> None:
    database.init_db()
    start_scheduler()

    tz = pytz.timezone(config.TIMEZONE)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    if not database.get_digest(today):
        logger.info("No digest for today — triggering initial fetch")
        asyncio.create_task(run_daily_fetch())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    stop_scheduler()


@app.get("/", include_in_schema=False)
async def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Daily News Podcast API — frontend not found"}


# ── Digest endpoints ──────────────────────────────────────────────────────────

@app.get("/api/digest/today")
async def get_today_digest():
    tz = pytz.timezone(config.TIMEZONE)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    return _build_response(today)


@app.get("/api/digest/{date}")
async def get_digest_by_date(date: str):
    digest = database.get_digest(date)
    if not digest:
        raise HTTPException(404, detail="No digest found for this date")
    return _build_response(date)


def _build_response(date: str) -> dict:
    digest = database.get_digest(date)
    articles = database.get_articles(date)
    papers = database.get_academic_papers(date)

    by_category: dict = {}
    for art in articles:
        by_category.setdefault(art["category"], []).append(art)

    return {
        "date": date,
        "digest": digest,
        "articles_by_category": by_category,
        "academic_papers": papers,
        "fetched": digest is not None,
    }


@app.post("/api/digest/refresh")
async def refresh_digest(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_daily_fetch)
    return {"message": "Refresh started", "status": "processing"}


# ── Settings endpoints ────────────────────────────────────────────────────────

class SettingsPayload(BaseModel):
    research_topics: Optional[List[str]] = None


@app.get("/api/settings")
async def get_settings():
    return {
        "research_topics": database.get_setting("research_topics", config.RESEARCH_TOPICS),
        "timezone": config.TIMEZONE,
        "daily_hour": config.DAILY_HOUR,
        "daily_minute": config.DAILY_MINUTE,
    }


@app.put("/api/settings")
async def update_settings(payload: SettingsPayload):
    if payload.research_topics is not None:
        database.save_setting("research_topics", payload.research_topics)
    return {
        "message": "Settings updated",
        "research_topics": database.get_setting("research_topics", config.RESEARCH_TOPICS),
    }


# ── History ───────────────────────────────────────────────────────────────────

@app.get("/api/history")
async def get_history():
    return database.get_history(30)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
