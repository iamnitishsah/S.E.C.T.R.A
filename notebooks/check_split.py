"""Step 2.3 check: split every downloaded 10-K and flag suspicious sections.
    python notebooks/check_split.py            # all filings
    python notebooks/check_split.py AAPL CVX   # some tickers
"""
import sys
import time
from pathlib import Path

from sectra.parsing.html_text import extract
from sectra.parsing.section_splitter import split

KEY_ITEMS = ("1A", "7")
EXPECTED = {"1A": (10_000, 300_000), "7": (10_000, 400_000)}   # plausible length ranges (chars)

tickers = sys.argv[1:] or sorted(p.name for p in Path("data/raw/filings").iterdir() if p.is_dir())
rows, flagged, start = [], [], time.monotonic()
for ticker in tickers:
    for path in sorted(Path("data/raw/filings", ticker).glob("*.htm")):
        doc = extract(path)
        secs = split(doc)
        cells, problems = [], []
        for code in KEY_ITEMS:
            s = secs.get(code)
            if s is None:
                cells.append(f"{code}: MISSING".ljust(24))
                problems.append(f"{code} missing")
                continue
            lo, hi = EXPECTED[code]
            mark = "" if lo <= s.length <= hi else " !"
            if mark:
                problems.append(f"{code} length {s.length:,}")
            method = "link" if s.method == "toc_link" else "text"
            cells.append(f"{code}: {s.length:>7,} {method}{mark}".ljust(24))
        period = path.name[:10]
        print(f"{ticker:6} {period}  {' '.join(cells)} items={len(secs)}")
        rows.append((ticker, period))
        if problems:
            flagged.append((ticker, period, problems, {c: secs[c].heading for c in KEY_ITEMS if c in secs}))

print(f"\n{len(rows)} filings in {time.monotonic() - start:.0f}s | "
      f"{len(rows) - len(flagged)} clean | {len(flagged)} flagged")
for ticker, period, problems, headings in flagged:
    print(f"  {ticker} {period}: {', '.join(problems)}")
    for code, h in headings.items():
        print(f"      {code} heading: {h[:90]!r}")