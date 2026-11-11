"""Find a company's annual reports in its EDGAR filing index."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator
import hashlib

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SUBMISSIONS_PAGE_URL = "https://data.sec.gov/submissions/{name}"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"


def fetch_submissions(client, cik: str, raw_dir: str | Path, refresh: bool = False) -> dict:
    """Company metadata + filing index. refresh=True picks up newly filed reports."""
    dest = Path(raw_dir) / "submissions" / f"CIK{cik}.json"
    return client.fetch_json(SUBMISSIONS_URL.format(cik=cik), dest, refresh=refresh)


def columns_to_rows(block: dict) -> list[dict]:
    """{"form": [a, b], "accessionNumber": [x, y]} -> [{"form": a, ...}, {"form": b, ...}]"""
    if not block:
        return []
    lengths = {k: len(v) for k, v in block.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"Columns have different lengths: {lengths}")
    keys = list(block)
    return [dict(zip(keys, values)) for values in zip(*(block[k] for k in keys))]


def iter_filings(client, sub: dict, raw_dir: str | Path) -> Iterator[dict]:
    """Yield filings newest-first: the 'recent' block, then older index pages.

    It is a generator, so older pages are only downloaded if the caller keeps
    asking for more rows. Old pages never change, so they are never refreshed.
    """
    yield from columns_to_rows(sub["filings"]["recent"])
    for page in sub["filings"].get("files", []):
        name = page["name"]
        block = client.fetch_json(
            SUBMISSIONS_PAGE_URL.format(name=name), Path(raw_dir) / "submissions" / name
        )
        yield from columns_to_rows(block)


def select_annual_reports(rows: Iterable[dict], forms=("10-K",), n: int = 4) -> list[dict]:
    """Latest n filings whose form matches exactly (so 10-K/A is excluded), newest first."""
    if isinstance(forms, str):
        forms = (forms,)  # a bare string would make `in` do substring matching
    picked, periods = [], set()
    for row in rows:
        if row.get("form") not in forms:
            continue
        period = row.get("reportDate") or row.get("filingDate")  # reportDate is sometimes blank
        if period in periods:
            continue  # same period filed twice: keep the newer one (seen first)
        periods.add(period)
        picked.append({**row, "period": period})
        if len(picked) == n:
            break  # stop early -> older index pages are never fetched
    return sorted(picked, key=lambda r: r["period"], reverse=True)


def archive_url(cik: str, accession: str, primary_doc: str) -> str:
    """Archives URLs use the CIK without zero-padding and the accession without dashes."""
    return ARCHIVE_URL.format(cik_int=int(cik), acc_nodash=accession.replace("-", ""), doc=primary_doc)


def filing_path(raw_dir: str | Path, ticker: str, report: dict) -> Path:
    """data/raw/filings/AAPL/2025-09-27_10-K_0000320193-25-000079.htm"""
    suffix = Path(report["primaryDocument"]).suffix or ".htm"
    name = f"{report['period']}_{report['form']}_{report['accessionNumber']}{suffix}"
    return Path(raw_dir) / "filings" / ticker / name


def download_filing(client, company: dict, report: dict, raw_dir: str | Path, root: str | Path) -> dict:
    """Download one filing's main document and return its manifest row.

    Filed documents never change, so they are never refreshed: a re-run reads
    them from disk. The SHA-256 lets anyone verify they have identical files.
    """
    url = archive_url(company["cik"], report["accessionNumber"], report["primaryDocument"])
    dest = filing_path(raw_dir, company["ticker"], report)
    content = client.fetch(url, dest)
    return {
        "accession_no": report["accessionNumber"],
        "cik": company["cik"],
        "ticker": company["ticker"],
        "form_type": report["form"],
        "filing_date": report["filingDate"],
        "period_of_report": report["period"],
        "primary_document": report["primaryDocument"],
        "primary_doc_url": url,
        "local_path": dest.relative_to(root).as_posix(),
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "is_inline_xbrl": int(report.get("isInlineXBRL") or 0),
    }