import os

RESEARCH_TOPICS: list[str] = [
    t.strip()
    for t in os.getenv(
        "RESEARCH_TOPICS",
        "artificial intelligence medicine,machine learning clinical,large language model healthcare,natural language processing biomedical,clinical decision support",
    ).split(",")
    if t.strip()
]

NEWS_FEEDS: dict = {
    "international": [
        {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
        {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss"},
        {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml"},
    ],
    "health": [
        {"name": "WHO", "url": "https://www.who.int/rss-feeds/news-english.xml"},
        {"name": "Medical Xpress", "url": "https://medicalxpress.com/rss-feed/"},
        {"name": "Science Daily Health", "url": "https://www.sciencedaily.com/rss/health.xml"},
        {"name": "NIH News", "url": "https://www.nih.gov/rss/news.xml"},
    ],
    "technology": [
        {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    ],
    "ai": [
        {"name": "MIT AI News", "url": "https://news.mit.edu/topic/artificial-intelligence2/rss.xml"},
        {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
        {
            "name": "Science Daily AI",
            "url": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
        },
    ],
    "taiwan": [
        {"name": "CNA 中央通訊社", "url": "https://www.cna.com.tw/rss/aall.aspx"},
        {"name": "Focus Taiwan", "url": "https://focustaiwan.tw/politics/rss"},
    ],
}

ACADEMIC_FEEDS: dict = {
    "nature": [
        {"name": "Nature", "url": "https://www.nature.com/nature.rss"},
        {"name": "Nature Medicine", "url": "https://www.nature.com/nm.rss"},
        {"name": "Nature Biomedical Engineering", "url": "https://www.nature.com/natbiomedeng.rss"},
    ],
    "nejm": [
        {
            "name": "NEJM",
            "url": "https://www.nejm.org/action/showFeed?jc=nejm&type=etoc&feed=rss",
        }
    ],
    "lancet": [
        {
            "name": "The Lancet",
            "url": "https://www.thelancet.com/rssfeed/lancet_current.xml",
        }
    ],
}

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DATABASE_PATH = os.getenv("DATABASE_PATH", "podcast.db")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Taipei")
DAILY_HOUR = int(os.getenv("DAILY_HOUR", "9"))
DAILY_MINUTE = int(os.getenv("DAILY_MINUTE", "0"))
MAX_NEWS_PER_CATEGORY = int(os.getenv("MAX_NEWS_PER_CATEGORY", "5"))
MAX_ACADEMIC_PAPERS = int(os.getenv("MAX_ACADEMIC_PAPERS", "8"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
