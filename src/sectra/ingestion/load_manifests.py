"""Load data/raw/manifest/*.csv into the companies and filings tables.

Idempotent: re-running updates rows in place instead of duplicating them.
    python -m sectra.ingestion.load_manifests
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import bindparam, text

from sectra.storage.mysql import get_engine

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data" / "raw" / "manifest"


def read_rows(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return [{k: (v if v != "" else None) for k, v in row.items()} for row in csv.DictReader(f)]


def table_columns(conn, table: str) -> set[str]:
    return set(conn.execute(text(f"SHOW COLUMNS FROM {table}")).scalars())  # first column = name


def upsert(conn, table: str, rows: list[dict], key: str) -> None:
    allowed = table_columns(conn, table)
    cols = [c for c in rows[0] if c in allowed]
    ignored = [c for c in rows[0] if c not in allowed]
    if ignored:
        print(f"{table}: ignoring CSV columns not in table: {', '.join(ignored)}")
    rows = [{c: r[c] for c in cols} for r in rows]

    updates = ", ".join(f"{c} = new.{c}" for c in cols if c != key)
    sql = text(
        f"INSERT INTO {table} ({', '.join(cols)}) "
        f"VALUES ({', '.join(':' + c for c in cols)}) AS new "
        f"ON DUPLICATE KEY UPDATE {updates}"
    )
    conn.execute(sql, rows)


def main() -> None:
    companies = read_rows(MANIFEST / "companies.csv")
    filings = read_rows(MANIFEST / "filings.csv")

    engine = get_engine()
    with engine.begin() as conn:  # one transaction: all or nothing
        upsert(conn, "companies", companies, key="cik")  # parents before children (FK)
        upsert(conn, "filings", filings, key="accession_no")

        # Filings no longer in the manifest (company removed from config) are deleted.
        stale = conn.execute(
            text("DELETE FROM filings WHERE accession_no NOT IN :ids")
            .bindparams(bindparam("ids", expanding=True)),
            {"ids": [f["accession_no"] for f in filings]},
            ).rowcount
        extra = conn.execute(
            text("SELECT ticker FROM companies WHERE cik NOT IN :ciks")
            .bindparams(bindparam("ciks", expanding=True)),
            {"ciks": [c["cik"] for c in companies]},
            ).scalars().all()

    print(f"companies: {len(companies)} upserted | filings: {len(filings)} upserted, {stale} stale removed")
    if extra:
        print(f"WARNING: companies in DB but not in manifest: {', '.join(extra)}")


if __name__ == "__main__":
    main()