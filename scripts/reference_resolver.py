#!/usr/bin/env python3
"""Resolve plain-text references into RIS, ENW, or BibTeX.

This script is intentionally conservative: network lookups enrich records when
available, but low-confidence matches are preserved from the input and reported.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from typing import Iterable

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
YEAR_RE = re.compile(r"\((19\d{2}|20\d{2})\)|\b(19\d{2}|20\d{2})\b")

@dataclass
class Ref:
    raw: str
    title: str = ""
    year: str = ""
    authors: list[str] | None = None
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    publisher: str = ""
    edition: str = ""
    ref_type: str = "GEN"
    confidence: float = 0.0
    status: str = "parsed"

    def __post_init__(self):
        if self.authors is None:
            self.authors = []


def normalize_title(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s.lower())).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def split_records(text: str) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    if len(blocks) > 1:
        return blocks
    # APA-like fallback: start a new record before a capitalized surname followed by initials and a year.
    parts = re.split(r"(?<=\.)\s+(?=[A-Z][A-Za-z'\-]+,\s+[A-Z]\.)", text.strip())
    return [p.strip() for p in parts if p.strip()]


def parse_reference(raw: str) -> Ref:
    ref = Ref(raw=raw)
    doi = DOI_RE.search(raw)
    if doi:
        ref.doi = doi.group(0).rstrip(".")
    url = re.search(r"https?://\S+", raw)
    if url:
        ref.url = url.group(0).rstrip(".")
    year = YEAR_RE.search(raw)
    if year:
        ref.year = next(g for g in year.groups() if g)

    # Authors are usually before the first year parenthesis.
    before_year = raw.split(f"({ref.year})", 1)[0] if ref.year and f"({ref.year})" in raw else raw.split(".", 1)[0]
    # APA author strings are usually repeated "Family, I." tokens.
    author_tokens = re.findall(r"[^\W\d_][^,]+,\s*(?:[A-Z]\.\s*)+", before_year)
    ref.authors = [a.strip() for a in author_tokens] or [before_year.strip().rstrip(".")]

    # Title is usually after the year. Protect common abbreviation periods inside edition statements.
    after_year = raw.split(f"({ref.year}).", 1)[-1].strip() if ref.year and f"({ref.year})." in raw else ""
    protected = after_year.replace("ed.).", "ed§).")
    if protected:
        title_part = protected.split(". ", 1)[0].replace("§", ".").strip()
        ref.title = re.sub(r"\s*\(\d+(?:st|nd|rd|th)?\s+ed\.\)$", "", title_part, flags=re.I).strip()
        rest = protected[len(protected.split(". ", 1)[0]):].replace("§", ".").lstrip(". ")
    else:
        rest = raw

    if "arxiv" in raw.lower():
        ref.ref_type = "GEN"
        ref.journal = "arXiv"
    elif re.search(r"\bjournal\b|doi\.org|\d+\s*\(\d+\)", raw, re.I):
        ref.ref_type = "JOUR"
    elif ref.publisher or re.search(r"\(\d+(st|nd|rd|th) ed\.\)", raw, re.I):
        ref.ref_type = "BOOK"
    # Simple journal/volume/pages extraction for APA articles.
    m = re.search(r"([^\.]+),\s*(\d+)\s*(?:\(([^)]+)\))?,\s*([0-9]+)[–-]([0-9]+)", rest)
    if m:
        ref.journal, ref.volume, ref.issue, sp, ep = [x or "" for x in m.groups()]
        ref.pages = f"{sp}-{ep}"
        ref.ref_type = "JOUR"
    ed = re.search(r"\((\d+(?:st|nd|rd|th)?\s+ed\.)\)", raw, re.I)
    if ed:
        ref.edition = ed.group(1)
        ref.ref_type = "BOOK"
    if ref.ref_type == "BOOK":
        tail = raw.rsplit(".", 1)[0]
        if tail and not tail.startswith("http"):
            ref.publisher = tail.split(".")[-1].strip()
    return ref


def crossref_search(ref: Ref, timeout: int = 15) -> dict | None:
    if not ref.title and not ref.doi:
        return None
    if ref.doi:
        url = "https://api.crossref.org/works/" + urllib.parse.quote(ref.doi)
    else:
        params = urllib.parse.urlencode({"query.title": ref.title, "rows": 3})
        url = "https://api.crossref.org/works?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "reference-resolver-agent/1.0 (mailto:example@example.com)"})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        data = json.load(fh)
    if ref.doi and data.get("message"):
        return data["message"]
    items = data.get("message", {}).get("items", [])
    return items[0] if items else None


def enrich_from_crossref(ref: Ref) -> Ref:
    try:
        item = crossref_search(ref)
        time.sleep(0.2)
    except Exception as exc:
        ref.status = f"network_error: {exc}"
        return ref
    if not item:
        ref.status = "not_found"
        return ref
    candidate_title = (item.get("title") or [""])[0]
    score = 1.0 if ref.doi and item.get("DOI", "").lower() == ref.doi.lower() else similarity(ref.title, candidate_title)
    ref.confidence = score
    if score < 0.75:
        ref.status = "needs_review"
        return ref
    ref.status = "resolved" if score >= 0.90 else "needs_review"
    ref.title = candidate_title or ref.title
    ref.doi = item.get("DOI", ref.doi)
    ref.url = item.get("URL", ref.url)
    ref.year = str(((item.get("published-print") or item.get("published-online") or item.get("created") or {}).get("date-parts") or [[ref.year]])[0][0])
    ref.authors = [f"{a.get('family','')}, {a.get('given','')}".strip(', ') for a in item.get("author", [])] or ref.authors
    ref.journal = (item.get("container-title") or [ref.journal])[0]
    ref.volume = item.get("volume", ref.volume)
    ref.issue = item.get("issue", ref.issue)
    ref.pages = item.get("page", ref.pages).replace("–", "-")
    ref.publisher = item.get("publisher", ref.publisher)
    typ = item.get("type", "")
    ref.ref_type = "BOOK" if "book" in typ else "JOUR" if "journal" in typ else "CONF" if "proceedings" in typ else ref.ref_type
    return ref


def ris_type(t: str) -> str:
    return {"JOUR": "JOUR", "BOOK": "BOOK", "CONF": "CONF"}.get(t, "GEN")


def to_ris(refs: Iterable[Ref]) -> str:
    out = []
    for r in refs:
        lines = [f"TY  - {ris_type(r.ref_type)}"]
        for a in r.authors or []:
            lines.append(f"AU  - {a}")
        if r.year: lines.append(f"PY  - {r.year}")
        if r.title: lines.append(f"TI  - {r.title}")
        if r.journal: lines.append(f"JO  - {r.journal}")
        if r.volume: lines.append(f"VL  - {r.volume}")
        if r.issue: lines.append(f"IS  - {r.issue}")
        if r.pages:
            sp_ep = re.split(r"[-–]", r.pages, maxsplit=1)
            lines.append(f"SP  - {sp_ep[0]}")
            if len(sp_ep) > 1: lines.append(f"EP  - {sp_ep[1]}")
        if r.edition: lines.append(f"ET  - {r.edition}")
        if r.publisher: lines.append(f"PB  - {r.publisher}")
        if r.doi: lines.append(f"DO  - {r.doi}")
        if r.url: lines.append(f"UR  - {r.url}")
        lines.append("ER  -")
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


def enw_type(t: str) -> str:
    return {"JOUR": "Journal Article", "BOOK": "Book", "CONF": "Conference Paper"}.get(t, "Generic")


def to_enw(refs: Iterable[Ref]) -> str:
    out = []
    for r in refs:
        lines = [f"%0 {enw_type(r.ref_type)}"]
        for a in r.authors or []: lines.append(f"%A {a}")
        if r.year: lines.append(f"%D {r.year}")
        if r.title: lines.append(f"%T {r.title}")
        if r.journal: lines.append(f"%J {r.journal}")
        if r.volume: lines.append(f"%V {r.volume}")
        if r.issue: lines.append(f"%N {r.issue}")
        if r.pages: lines.append(f"%P {r.pages}")
        if r.edition: lines.append(f"%7 {r.edition}")
        if r.publisher: lines.append(f"%I {r.publisher}")
        if r.doi: lines.append(f"%R {r.doi}")
        if r.url: lines.append(f"%U {r.url}")
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


def bib_key(r: Ref, i: int) -> str:
    first = (r.authors[0].split(",")[0] if r.authors else "ref")
    return re.sub(r"\W+", "", f"{first}{r.year or i}") or f"ref{i}"


def to_bib(refs: Iterable[Ref]) -> str:
    entries = []
    for i, r in enumerate(refs, 1):
        kind = "book" if r.ref_type == "BOOK" else "article"
        fields = {
            "title": r.title,
            "author": " and ".join(r.authors or []),
            "year": r.year,
            "journal": r.journal if kind == "article" else "",
            "volume": r.volume,
            "number": r.issue,
            "pages": r.pages,
            "publisher": r.publisher if kind == "book" else "",
            "doi": r.doi,
            "url": r.url,
        }
        lines = [f"@{kind}{{{bib_key(r, i)},"]
        for k, v in fields.items():
            if v:
                lines.append(f"  {k} = {{{v}}},")
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--format", choices=["ris", "enw", "bib"], default="ris")
    ap.add_argument("--output", required=True)
    ap.add_argument("--report", default="")
    ap.add_argument("--no-network", action="store_true")
    args = ap.parse_args()
    text = open(args.input, encoding="utf-8").read()
    refs = [parse_reference(r) for r in split_records(text)]
    if not args.no_network:
        refs = [enrich_from_crossref(r) for r in refs]
    data = {"ris": to_ris, "enw": to_enw, "bib": to_bib}[args.format](refs)
    open(args.output, "w", encoding="utf-8").write(data)
    report_path = args.report or args.output + ".report.json"
    open(report_path, "w", encoding="utf-8").write(json.dumps([asdict(r) for r in refs], ensure_ascii=False, indent=2))
    print(f"wrote {args.output}")
    print(f"wrote {report_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
