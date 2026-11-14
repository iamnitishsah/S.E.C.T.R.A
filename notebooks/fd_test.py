import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from sectra.ingestion.company_resolver import load_ticker_map, load_universe, resolve
from sectra.ingestion.edgar_client import EdgarClient
from sectra.ingestion.filing_downloader import (
    archive_url, fetch_submissions, iter_filings, select_annual_reports,
)

logging.basicConfig(level=logging.INFO)
load_dotenv()
DATA = Path("data")
client = EdgarClient(os.environ["SEC_USER_AGENT"])

companies = resolve(load_universe("configs/companies.yaml"), load_ticker_map(client, DATA / "cache"))
print(f"Resolved {len(companies)} companies")

for c in [x for x in companies if x["ticker"] in {"AAPL", "NVDA"}]:
    before = client.network_calls
    sub = fetch_submissions(client, c["cik"], DATA / "raw")
    reports = select_annual_reports(iter_filings(client, sub, DATA / "raw"), n=4)
    print(f"\n{c['ticker']} ({c['name']}) | network calls: {client.network_calls - before}")
    for r in reports:
        print(f"  filed {r['filingDate']}  period {r['period']}  {r['accessionNumber']}")
        print(f"    {archive_url(c['cik'], r['accessionNumber'], r['primaryDocument'])}")