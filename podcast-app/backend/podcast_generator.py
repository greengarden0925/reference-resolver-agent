from datetime import datetime
from typing import Dict, List

import pytz

import config

_WEEKDAYS = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
_CATEGORY_LABELS: Dict[str, str] = {
    "international": "國際要聞",
    "health": "醫療健康",
    "technology": "科技新聞",
    "ai": "人工智慧",
    "taiwan": "台灣要聞",
}
_ORDINALS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def _ordinal(n: int) -> str:
    return _ORDINALS[n - 1] if 1 <= n <= len(_ORDINALS) else str(n)


def _fmt_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = _WEEKDAYS[dt.weekday()]
        return f"{dt.year}年{dt.month}月{dt.day}日，{weekday}"
    except ValueError:
        return date_str


def generate_podcast_script(
    date: str,
    news: Dict[str, List[dict]],
    academic_papers: List[dict],
) -> str:
    lines: List[str] = []
    date_cn = _fmt_date(date)

    lines += [
        f"早安！歡迎收聽每日新聞播報。",
        f"今天是 {date_cn}。",
        "以下為今日精選重要新聞，讓我們一起來看看今天的世界發生了什麼事。",
        "",
    ]

    # News sections
    section_order = ["international", "health", "technology", "ai", "taiwan"]
    for cat in section_order:
        articles = news.get(cat, [])
        if not articles:
            continue
        label = _CATEGORY_LABELS.get(cat, cat)
        lines.append(f"【{label}】")
        for i, art in enumerate(articles[:4], 1):
            title = art.get("title", "").strip()
            summary = art.get("summary", "").strip()
            source = art.get("source", "")
            lines.append(f"第{_ordinal(i)}則，來自 {source}：{title}")
            if summary:
                lines.append(f"  {summary}")
        lines.append("")

    # Academic section
    if academic_papers:
        lines += [
            "【學術焦點 — Nature、NEJM 與 PubMed 精選】",
            "以下為本週與您研究領域相關的最新學術文章：",
            "",
        ]
        for i, paper in enumerate(academic_papers[:6], 1):
            title = paper.get("title", "").strip()
            source = paper.get("source", "")
            authors = paper.get("authors", "")
            abstract = (paper.get("abstract") or "").strip()
            lines.append(f"第{_ordinal(i)}篇：《{title}》")
            if source:
                lines.append(f"  來源：{source}")
            if authors:
                lines.append(f"  作者：{authors}")
            if abstract:
                snippet = abstract[:250]
                if len(abstract) > 250:
                    snippet = snippet.rsplit(" ", 1)[0] + "…"
                lines.append(f"  摘要：{snippet}")
            lines.append("")

    lines += [
        "以上是今日的每日新聞播報。",
        "感謝您的收聽，祝您有個充實愉快的一天，再見！",
    ]

    return "\n".join(lines)
