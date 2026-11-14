"""Step 2.2 check: run the extractor on real filings and save the text for eyeballing.
    python notebooks/check_extract.py AAPL MSFT CVX
"""
import re
import sys
from pathlib import Path

from sectra.parsing.html_text import extract

TITLE_RE = re.compile(r"item\s*(1a|7)\b|risk factors|management.s discussion", re.I)

for ticker in sys.argv[1:]:
    path = sorted(Path("data/raw/filings", ticker).glob("*.htm"))[-1]
    d = extract(path)
    targets = {t for _, t in d.links}
    print(f"\n=== {ticker}: {len(d.text):,} chars | {d.text.count('[TABLE]')} tables | "
          f"{len(d.anchors)}/{len(targets)} link targets located")
    print("  boilerplate removed (top 8):", d.removed_lines.most_common(8))

    seen = set()
    for label, target in d.links:
        if TITLE_RE.search(label) and target not in seen and target in d.anchors:
            seen.add(target)
            off = d.anchors[target]
            snippet = d.text[off: off + 80].replace("\n", " | ")
            print(f"  {label[:40]!r:42} -> {off / len(d.text):6.1%}: {snippet!r}")

    out = Path("data/processed/text") / ticker / f"{path.stem}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(d.text)
    print("  saved", out)