"""XBRL company facts: download now"""

from __future__ import annotations

from pathlib import Path

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def fetch_company_facts(client, cik: str, raw_dir: str | Path, refresh: bool = False) -> Path:
    """Every XBRL fact the company has ever reported, in one JSON file."""
    dest = Path(raw_dir) / "xbrl" / f"CIK{cik}.json"
    client.fetch(COMPANYFACTS_URL.format(cik=cik), dest, refresh=refresh)  # raw bytes: no need to parse here
    return dest