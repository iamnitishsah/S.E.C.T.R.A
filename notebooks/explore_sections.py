"""Phase 2 exploration: how do 10-K Item headings appear in the raw HTML?
    python notebooks/explore_sections.py AAPL MSFT CVX
"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ITEM_RE = re.compile(
    r"\bitem\s*(1a|1b|1c|1|2|3|4|5|6|7a|7|8|9a|9b|9c|9|10|11|12|13|14|15|16)\b[\s.:\-—–]",
    re.IGNORECASE,
)


def latest_filing(ticker: str) -> Path:
    return sorted(Path("data/raw/filings", ticker).glob("*.htm"))[-1]


def load(path: Path):
    soup = BeautifulSoup(path.read_bytes(), "lxml")
    for tag in soup.find_all(["script", "style", "ix:header"]):
        tag.decompose()  # ix:header = hidden XBRL contexts, not readable text
    text = soup.get_text("\n")
    text = re.sub(r"[ \t\xa0]+", " ", text)   # \xa0 = non-breaking space, common in filings
    text = re.sub(r"\n\s*\n+", "\n", text)
    return soup, text


for ticker in sys.argv[1:]:
    path = latest_filing(ticker)
    soup, text = load(path)
    print(f"\n=== {ticker}: {path.name} | {len(text):,} chars of text")

    # 1. Table-of-contents links: do they exist, and do their targets exist?
    links = [(a.get_text(" ", strip=True), a["href"][1:])
             for a in soup.find_all("a", href=True) if a["href"].startswith("#")]
    item_links = [(t, h) for t, h in links if re.search(r"item|risk|management", t, re.I)]
    resolvable = sum(1 for _, h in item_links if soup.find(id=h) or soup.find(attrs={"name": h}))
    print(f"internal links: {len(links)} | item-like: {len(item_links)} | targets found: {resolvable}")
    for t, h in item_links[:12]:
        print(f"   {t[:55]!r:58} -> #{h}")

    # 2. Every place the text says "Item 1A" or "Item 7": TOC entry vs. real heading?
    for m in ITEM_RE.finditer(text):
        if m.group(1).lower() in ("1a", "7"):
            ctx = text[m.start(): m.start() + 90].replace("\n", " | ")
            print(f"  Item {m.group(1):>2} at {m.start() / len(text):6.1%} of doc: {ctx!r}")