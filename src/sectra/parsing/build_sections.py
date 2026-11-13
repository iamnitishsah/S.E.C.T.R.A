"""Split every 10-K in the filings table into Items and store the results.

    python -m sectra.parsing.build_sections

Writes, for each filing:
  data/processed/text/<TICKER>/<accession>.txt               full clean text (offsets refer to this)
  data/processed/sections/<TICKER>/<accession>/<item>.txt    one file per Item
  filing_sections table                                      one row per (filing, Item)
and once:
  eval/results/section_parse_report.csv                      every section, for review
Safe to re-run: each filing's sections are replaced atomically.
"""

from __future__ import annotations

import csv
import shutil
import time
from pathlib import Path

from sqlalchemy import text

from sectra.parsing.html_text import extract
from sectra.parsing.section_splitter import split
from sectra.storage.mysql import get_engine

ROOT = Path(__file__).resolve().parents[3]
KEY_ITEMS = ("1A", "7")
EXPECTED = {"1A": (10_000, 300_000), "7": (10_000, 400_000)}   # plausible lengths (chars)
COLUMNS = ["accession_no", "item_code", "heading", "char_start", "char_end",
           "n_chars", "method", "quality", "text_path"]
INSERT = text(f"INSERT INTO filing_sections ({', '.join(COLUMNS)}) "
              f"VALUES ({', '.join(':' + c for c in COLUMNS)})")


def quality(code: str, n_chars: int) -> str:
    lo, hi = EXPECTED.get(code, (0, 10**9))
    return "ok" if lo <= n_chars <= hi else "suspect"


def build(root: Path, engine) -> list[dict]:
    with engine.connect() as conn:
        filings = conn.execute(text(
            "SELECT f.accession_no, c.ticker, f.fiscal_year, f.local_path "
            "FROM filings f JOIN companies c ON c.cik = f.cik "
            "ORDER BY c.ticker, f.fiscal_year"
        )).mappings().all()

    report = []
    for f in filings:
        acc, ticker = f["accession_no"], f["ticker"]
        doc = extract(root / f["local_path"])
        sections = split(doc)

        text_rel = Path("data/processed/text") / ticker / f"{acc}.txt"
        (root / text_rel).parent.mkdir(parents=True, exist_ok=True)
        (root / text_rel).write_text(doc.text, encoding="utf-8")

        sec_dir = root / "data/processed/sections" / ticker / acc
        shutil.rmtree(sec_dir, ignore_errors=True)          # no stale Items from earlier runs
        sec_dir.mkdir(parents=True)

        rows = []
        for code, s in sections.items():
            sec_rel = sec_dir.relative_to(root) / f"{code}.txt"
            (root / sec_rel).write_text(doc.text[s.start:s.end], encoding="utf-8")
            row = {
                "accession_no": acc, "item_code": code, "heading": s.heading[:255],
                "char_start": s.start, "char_end": s.end, "n_chars": s.length,
                "method": s.method, "quality": quality(code, s.length), "text_path": sec_rel.as_posix(),
            }
            rows.append(row)
            report.append({"ticker": ticker, "fiscal_year": f["fiscal_year"], **row,
                           "ends_at": doc.text[s.end:s.end + 80].split("\n")[0]})
        for code in KEY_ITEMS:                               # missing key Items show up in the report
            if code not in sections:
                report.append({"ticker": ticker, "fiscal_year": f["fiscal_year"], "accession_no": acc,
                               "item_code": code, "quality": "missing"})

        with engine.begin() as conn:                         # replace this filing's rows atomically
            conn.execute(text("DELETE FROM filing_sections WHERE accession_no = :a"), {"a": acc})
            if rows:
                conn.execute(INSERT, rows)

        key = {r["item_code"]: r for r in rows if r["item_code"] in KEY_ITEMS}
        status = "  ".join(f"{c}:{key[c]['n_chars']:>8,} {key[c]['quality']:7}" if c in key
                           else f"{c}: missing        " for c in KEY_ITEMS)
        print(f"{ticker:6} FY{f['fiscal_year']}  {len(rows):2} items  {status}")
    return report


def write_report(root: Path, report: list[dict]) -> None:
    out = root / "eval/results/section_parse_report.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["ticker", "fiscal_year", "accession_no", "item_code", "n_chars", "method",
              "quality", "heading", "ends_at", "char_start", "char_end", "text_path"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(report)

    filings = {r["accession_no"] for r in report}
    good = {a for a in filings
            if all(any(r["accession_no"] == a and r["item_code"] == c and r["quality"] == "ok" for r in report)
                   for c in KEY_ITEMS)}
    print(f"\n{len(filings)} filings | {len(good)} with Items 1A and 7 both ok "
          f"({len(good) / max(len(filings), 1):.1%}) | report: {out.relative_to(root)}")
    for r in report:
        if r["item_code"] in KEY_ITEMS and r["quality"] != "ok":
            print(f"  {r['ticker']} FY{r['fiscal_year']} Item {r['item_code']}: {r['quality']}"
                  + (f" ({r['n_chars']:,} chars) starts {r['heading'][:60]!r}" if r.get("n_chars") else ""))


def main() -> None:
    start = time.monotonic()
    report = build(ROOT, get_engine())
    write_report(ROOT, report)
    print(f"done in {time.monotonic() - start:.0f}s")


if __name__ == "__main__":
    main()