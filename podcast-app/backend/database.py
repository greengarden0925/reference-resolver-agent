import json
import sqlite3
from contextlib import contextmanager

import config


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_digest (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL UNIQUE,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                podcast_script TEXT
            );

            CREATE TABLE IF NOT EXISTS news_articles (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                digest_date  TEXT NOT NULL,
                category     TEXT NOT NULL,
                source       TEXT,
                title        TEXT,
                summary      TEXT,
                url          TEXT,
                published_at TEXT
            );

            CREATE TABLE IF NOT EXISTS academic_papers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                digest_date     TEXT NOT NULL,
                source          TEXT,
                title           TEXT,
                authors         TEXT,
                abstract        TEXT,
                url             TEXT,
                doi             TEXT,
                published_at    TEXT,
                relevance_score REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        conn.commit()


def save_digest(date: str, podcast_script: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO daily_digest (date, podcast_script) VALUES (?, ?)",
            (date, podcast_script),
        )
        conn.commit()


def save_articles(date: str, category: str, articles: list) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM news_articles WHERE digest_date=? AND category=?",
            (date, category),
        )
        conn.executemany(
            "INSERT INTO news_articles (digest_date, category, source, title, summary, url, published_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    date,
                    category,
                    a.get("source"),
                    a.get("title"),
                    a.get("summary"),
                    a.get("url"),
                    a.get("published_at"),
                )
                for a in articles
            ],
        )
        conn.commit()


def save_academic_papers(date: str, papers: list) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM academic_papers WHERE digest_date=?", (date,))
        conn.executemany(
            "INSERT INTO academic_papers"
            " (digest_date, source, title, authors, abstract, url, doi, published_at, relevance_score)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    date,
                    p.get("source"),
                    p.get("title"),
                    p.get("authors"),
                    p.get("abstract"),
                    p.get("url"),
                    p.get("doi"),
                    p.get("published_at"),
                    p.get("relevance_score", 0),
                )
                for p in papers
            ],
        )
        conn.commit()


def get_digest(date: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM daily_digest WHERE date=?", (date,)
        ).fetchone()
        return dict(row) if row else None


def get_articles(date: str, category: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM news_articles WHERE digest_date=? AND category=? ORDER BY id",
                (date, category),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM news_articles WHERE digest_date=? ORDER BY category, id",
                (date,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_academic_papers(date: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM academic_papers WHERE digest_date=? ORDER BY relevance_score DESC, id",
            (date,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_setting(key: str, default=None):
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default


def save_setting(key: str, value) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        conn.commit()


def get_history(limit: int = 30) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT date, created_at FROM daily_digest ORDER BY date DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
