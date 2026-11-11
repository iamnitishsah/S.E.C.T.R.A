"""Map the tickers in configs/companies.yaml to SEC CIKs."""

from __future__ import annotations

from pathlib import Path

import yaml

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def load_config(yaml_path: str | Path) -> dict:
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def load_universe(yaml_path: str | Path) -> list[tuple[str, str]]:
    """Return [(ticker, sector), ...] in the order they appear in the YAML."""
    cfg = load_config(yaml_path)
    universe, seen = [], set()
    for sector, tickers in (cfg.get("sectors") or {}).items():
        for t in tickers or []:
            # YAML 1.1 reads bare ON / NO / YES as booleans -> quote such tickers
            if not isinstance(t, str):
                raise ValueError(f"Ticker {t!r} in sector '{sector}' is not a string; quote it in the YAML")
            t = t.strip().upper()
            if t in seen:
                raise ValueError(f"{t} is listed more than once in {yaml_path}")
            seen.add(t)
            universe.append((t, sector))
    if not universe:
        raise ValueError(f"No tickers found in {yaml_path}")
    return universe


def load_ticker_map(client, cache_dir: str | Path, refresh: bool = False) -> dict[str, dict]:
    """Return {"AAPL": {"cik": "0000320193", "name": "Apple Inc."}, ...}."""
    data = client.fetch_json(TICKERS_URL, Path(cache_dir) / "company_tickers.json", refresh=refresh)
    ticker_map = {}
    for row in data.values():  # file shape: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "..."}, ...}
        ticker_map.setdefault(
            row["ticker"].upper(),
            {"cik": f"{int(row['cik_str']):010d}", "name": row["title"]},
        )
    return ticker_map


def resolve(universe: list[tuple[str, str]], ticker_map: dict[str, dict]) -> list[dict]:
    """Return [{"ticker", "sector", "cik", "name"}, ...]; fail listing every unknown ticker."""
    missing = [t for t, _ in universe if t not in ticker_map]
    if missing:
        raise KeyError(f"Not in SEC ticker map: {', '.join(missing)}")
    return [{"ticker": t, "sector": s, **ticker_map[t]} for t, s in universe]