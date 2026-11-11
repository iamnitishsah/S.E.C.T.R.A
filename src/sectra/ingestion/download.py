"""Download the starter dataset: filing index, 10-K documents, XBRL company facts.

Run from the project root:
    python -m sectra.ingestion.download                      # every company in configs/companies.yaml
    python -m sectra.ingestion.download --tickers AAPL NVDA  # a quick subset
    python -m sectra.ingestion.download --refresh            # re-pull indexes to catch new filings
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from sectra.ingestion.company_resolver import load_config, load_ticker_map, load_universe, resolve
from sectra.ingestion.edgar_client import EdgarClient
from sectra.ingestion.filing_downloader import (
    download_filing, fetch_submissions, iter_filings, select_annual_reports,
)
from sectra.ingestion.xbrl_loader import fetch_company_facts

log = logging.getLogger("sectra.download")

ROOT = Path(__file__).resolve().parents[3]  # src/sectra/ingestion/download.py -> project root

# Column names match the MySQL tables planned in the README, so Phase 1 can load these directly.
COMPANY_FIELDS = ["cik", "ticker", "name", "sector", "sic", "sic_description", "exchange", "fiscal_year_end"]
FILING_FIELDS = [
    "accession_no", "cik", "ticker", "form_type", "filing_date", "period_of_report",
    "primary_document", "primary_doc_url", "local_path", "size_bytes", "sha256", "is_inline_xbrl",
]


def company_metadata(company: dict, sub: dict) -> dict:
    exchanges = sub.get("exchanges") or [""]
    return {
        "cik": company["cik"],
        "ticker": company["ticker"],
        "name": sub.get("name") or company["name"],
        "sector": company["sector"],
        "sic": sub.get("sic", ""),
        "sic_description": sub.get("sicDescription", ""),
        "exchange": exchanges[0],
        "fiscal_year_end": sub.get("fiscalYearEnd", ""),  # "MMDD", e.g. "0927" for Apple
    }


def write_manifest(path: Path, fields: list[str], new_rows: list[dict], replaced: set[str], in_scope: set[str], sort_key) -> None:
    """Rewrite a manifest CSV: keep earlier rows only for in-scope companies not processed this run."""
    rows = []
    if path.exists():
        with open(path, newline="") as f:
            rows = [r for r in csv.DictReader(f)
                    if r["ticker"] not in replaced and r["ticker"] in in_scope]
    rows += new_rows
    rows.sort(key=sort_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(root: Path, client, tickers=None, per_company=None, refresh=False, skip_xbrl=False) -> int:
    cfg_path = root / "configs" / "companies.yaml"
    cfg = load_config(cfg_path)
    forms = tuple(cfg["filings"]["forms"])
    n = per_company or cfg["filings"]["per_company"]
    raw = root / "data" / "raw"

    universe = load_universe(cfg_path)
    in_scope = {t for t, _ in universe}
    if tickers:
        wanted = {t.upper() for t in tickers}
        unknown = wanted - {t for t, _ in universe}
        if unknown:
            raise SystemExit(f"Not in configs/companies.yaml: {', '.join(sorted(unknown))}")
        universe = [u for u in universe if u[0] in wanted]

    companies = resolve(universe, load_ticker_map(client, root / "data" / "cache", refresh=refresh))
    log.info("Downloading %d companies, latest %d x %s each", len(companies), n, "/".join(forms))

    company_rows, filing_rows, failures = [], [], {}
    start = time.monotonic()
    for i, c in enumerate(companies, 1):
        before = client.network_calls
        try:
            sub = fetch_submissions(client, c["cik"], raw, refresh=refresh)
            reports = select_annual_reports(iter_filings(client, sub, raw), forms=forms, n=n)
            if not reports:
                raise LookupError(f"no {'/'.join(forms)} filings under CIK {c['cik']}")
            if len(reports) < n:
                log.warning("%s: only %d of %d filings found", c["ticker"], len(reports), n)
            rows = [download_filing(client, c, r, raw, root) for r in reports]
            if not skip_xbrl:
                fetch_company_facts(client, c["cik"], raw, refresh=refresh)
        except PermissionError:
            raise  # 403 = bad User-Agent or SEC block: stop now, don't keep hitting SEC
        except Exception as exc:  # one bad company shouldn't kill the run
            failures[c["ticker"]] = repr(exc)
            log.error("[%d/%d] %s failed: %r", i, len(companies), c["ticker"], exc)
            continue
        company_rows.append(company_metadata(c, sub))
        filing_rows.extend(rows)
        log.info("[%d/%d] %-5s %d filings | %d network calls",
                 i, len(companies), c["ticker"], len(rows), client.network_calls - before)

    done = {r["ticker"] for r in company_rows}
    manifest = raw / "manifest"
    write_manifest(manifest / "companies.csv", COMPANY_FIELDS, company_rows, done, in_scope,
                   lambda r: (r["sector"], r["ticker"]))
    write_manifest(manifest / "filings.csv", FILING_FIELDS, filing_rows, done, in_scope,
                   lambda r: (r["ticker"], r["period_of_report"]))
    (manifest / "last_run.json").write_text(json.dumps({
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "companies_ok": len(company_rows),
        "filings_ok": len(filing_rows),
        "forms": list(forms),
        "per_company": n,
        "refresh": refresh,
        "network_calls": client.network_calls,
        "seconds": round(time.monotonic() - start, 1),
        "failures": failures,
    }, indent=2))

    log.info("Done: %d companies, %d filings, %d network calls, %.0fs",
             len(company_rows), len(filing_rows), client.network_calls, time.monotonic() - start)
    if failures:
        log.error("Failed: %s", ", ".join(failures))
    return 1 if failures else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tickers", nargs="+", help="only these tickers (must be in companies.yaml)")
    p.add_argument("--per-company", type=int, help="override filings.per_company from the YAML")
    p.add_argument("--refresh", action="store_true", help="re-download indexes and XBRL to pick up new filings")
    p.add_argument("--skip-xbrl", action="store_true", help="filings only")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    load_dotenv(ROOT / ".env")
    ua = os.getenv("SEC_USER_AGENT", "").strip()
    if "@" not in ua:
        raise SystemExit('Set SEC_USER_AGENT="Your Name you@email.com" in .env')

    return run(ROOT, EdgarClient(ua), args.tickers, args.per_company, args.refresh, args.skip_xbrl)


if __name__ == "__main__":
    sys.exit(main())