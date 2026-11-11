"""Load sql/metric_map.csv into the metric_map table (full replace, one transaction).
    python -m sectra.ingestion.load_metric_map
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import text

from sectra.storage.mysql import get_engine

ROOT = Path(__file__).resolve().parents[3]
COLUMNS = ["canonical_metric", "taxonomy", "tag", "unit", "period_type", "priority", "cik"]


def read_map(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        rows = [{c: (r.get(c) or "").strip() for c in COLUMNS} for r in csv.DictReader(f)]
    seen = set()
    for i, r in enumerate(rows, start=2):  # line 1 is the header
        key = (r["canonical_metric"], r["cik"], r["priority"])
        if key in seen:
            raise ValueError(f"line {i}: duplicate priority {key}")
        seen.add(key)
        if r["period_type"] not in ("duration", "instant"):
            raise ValueError(f"line {i}: period_type must be duration or instant, got {r['period_type']!r}")
        if not r["priority"].isdigit():
            raise ValueError(f"line {i}: priority must be a positive integer")
        if r["cik"] and len(r["cik"]) != 10:
            raise ValueError(f"line {i}: cik must be 10 digits, zero-padded")
    return rows


def main() -> None:
    rows = read_map(ROOT / "sql" / "metric_map.csv")
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM metric_map"))  # not TRUNCATE: it commits implicitly, breaking the transaction
        conn.execute(
            text(f"INSERT INTO metric_map ({', '.join(COLUMNS)}) "
                 f"VALUES ({', '.join(':' + c for c in COLUMNS)})"),
            rows,
        )
    print(f"metric_map: {len(rows)} rows, {len({r['canonical_metric'] for r in rows})} metrics")


if __name__ == "__main__":
    main()