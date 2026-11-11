"""XBRL company facts"""

from __future__ import annotations

from pathlib import Path
import json
import time
from decimal import Decimal
from itertools import islice
from typing import Iterator

from sqlalchemy import text

from sectra.storage.mysql import get_engine

ROOT = Path(__file__).resolve().parents[3]
BATCH = 5000
COLUMNS = ["cik", "taxonomy", "tag", "unit", "value", "period_start", "period_end",
           "filing_fy", "filing_fp", "form", "accession_no", "filed_date", "frame"]
MAX_LEN = {"taxonomy": 20, "tag": 255, "unit": 50, "filing_fp": 4,
           "form": 20, "accession_no": 20, "frame": 20}  # must match sql/schema.sql
INSERT_SQL = text(
    f"INSERT INTO financial_facts ({', '.join(COLUMNS)}) "
    f"VALUES ({', '.join(':' + c for c in COLUMNS)})"
)

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def fetch_company_facts(client, cik: str, raw_dir: str | Path, refresh: bool = False) -> Path:
    """Every XBRL fact the company has ever reported, in one JSON file."""
    dest = Path(raw_dir) / "xbrl" / f"CIK{cik}.json"
    client.fetch(COMPANYFACTS_URL.format(cik=cik), dest, refresh=refresh)  # raw bytes: no need to parse here
    return dest

def iter_facts(data: dict, cik: str) -> Iterator[dict]:
    """Flatten companyfacts JSON: facts -> taxonomy -> tag -> units -> unit -> [fact, ...]"""
    for taxonomy, tags in data.get("facts", {}).items():
        for tag, body in tags.items():
            for unit, facts in body.get("units", {}).items():
                for f in facts:
                    row = {
                        "cik": cik,
                        "taxonomy": taxonomy,
                        "tag": tag,
                        "unit": unit,
                        "value": f["val"],
                        "period_start": f.get("start"),  # missing for instant facts
                        "period_end": f["end"],
                        "filing_fy": f.get("fy"),        # fiscal year of the FILING
                        "filing_fp": f.get("fp"),
                        "form": f["form"],
                        "accession_no": f["accn"],
                        "filed_date": f["filed"],
                        "frame": f.get("frame"),         # only on SEC's chosen fact per period
                    }
                    for col, limit in MAX_LEN.items():
                        if row[col] is not None and len(str(row[col])) > limit:
                            raise ValueError(f"{col}={row[col]!r} exceeds {limit} chars (widen it in schema.sql)")
                    yield row


def batched(it: Iterator, n: int) -> Iterator[list]:
    while chunk := list(islice(it, n)):
        yield chunk


def load_company(conn, cik: str, path: Path) -> int:
    """Replace one company's facts. Run inside a transaction so delete + insert is atomic."""
    data = json.loads(path.read_bytes(), parse_float=Decimal)  # exact decimals, never binary floats
    conn.execute(text("DELETE FROM financial_facts WHERE cik = :cik"), {"cik": cik})
    n = 0
    for chunk in batched(iter_facts(data, cik), BATCH):
        conn.execute(INSERT_SQL, chunk)
        n += len(chunk)
    return n


def main() -> None:
    engine = get_engine()
    xbrl_dir = ROOT / "data" / "raw" / "xbrl"
    with engine.connect() as conn:  # the DB, not the folder, decides which companies are in scope
        companies = conn.execute(text("SELECT cik, ticker FROM companies ORDER BY ticker")).all()

    total, start = 0, time.monotonic()
    for cik, ticker in companies:
        path = xbrl_dir / f"CIK{cik}.json"
        if not path.exists():
            print(f"{ticker:6} no XBRL file, skipped")
            continue
        t0 = time.monotonic()
        with engine.begin() as conn:  # one transaction per company
            n = load_company(conn, cik, path)
        total += n
        print(f"{ticker:6} {n:>8,} facts  {time.monotonic() - t0:5.1f}s")
    print(f"Loaded {total:,} facts for {len(companies)} companies in {time.monotonic() - start:.0f}s")


if __name__ == "__main__":
    main()