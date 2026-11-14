# Data acquisition

What the SEC publishes, which part of it this project uses, and how it is downloaded.

## Background: SEC, EDGAR, XBRL

**SEC** (U.S. Securities and Exchange Commission) regulates U.S. securities markets. Publicly traded companies must disclose their finances, risks, and material events on a fixed schedule.

**EDGAR** is the SEC's public filing database, with free programmatic access through `data.sec.gov`.

| Form | Content | Frequency | Used here |
|---|---|---|---|
| **10-K** | Annual report: business, risks, audited financials | Yearly | ✅ |
| 10-Q | Quarterly report, unaudited | Three per year | Facts only (via XBRL) |
| 8-K | Material events | As they occur | ❌ |

## Structure of a 10-K

| Part | Item | Content | Indexed for RAG |
|---|---|---|---|
| I | **1** | Business | ✅ |
| I | **1A** | **Risk Factors** | ✅ (also the basis of risk diffing) |
| I | **1C** | Cybersecurity (required for fiscal years ending on/after 15 Dec 2023) | ✅ |
| I | **3** | Legal Proceedings | ✅ |
| II | **7** | **MD&A**: management's explanation of the numbers | ✅ |
| II | **7A** | Market risk | ✅ |
| II | 8 | Financial statements | ❌ (numbers come from XBRL) |

## XBRL

**XBRL** (eXtensible Business Reporting Language) tags every reported number with a standard concept such as `us-gaap:Revenues` or `us-gaap:NetIncomeLoss`. Modern 10-Ks use **inline XBRL**: the tags are embedded in the HTML document itself. The SEC extracts them into one JSON file per company (*companyfacts*), covering every filing back to about 2009. That JSON is **structured but not clean**, and [Financial database](02-financial-database.md) explains why.

## Dataset scope

| | |
|---|---|
| Companies | **20** across **4 sectors**: technology (AAPL, MSFT, GOOGL, AMZN, META), semiconductors (NVDA, AMD, INTC, QCOM, AVGO), healthcare (JNJ, PFE, MRK, ABBV, LLY), energy (CVX, COP, MPC, SLB, EOG) |
| Filings | Latest **4** annual 10-Ks per company = **80** filings, periods 2022-10-30 to 2026-09-27 |
| Documents | 313 MB of 10-K HTML |
| XBRL | **534,026** fact rows (**221,215** after SEC frame dedup), 12,229 distinct concepts, history back to ~2009 |
| Text | 1,784 extracted sections → **11,540** chunks |

Banks are configured but disabled: they report revenue under different XBRL concepts and have no gross-profit line, so they are added after the metric map is extended. The full per-company table is generated into [`dataset.md`](dataset.md).

## Sources

| Source | Content | Destination |
|---|---|---|
| `www.sec.gov/files/company_tickers.json` | Ticker → CIK map (~10,400 companies) | `data/cache/` |
| `data.sec.gov/submissions/CIK##########.json` | Company profile + complete filing index | `companies` table, filing selection |
| `data.sec.gov/api/xbrl/companyfacts/CIK##########.json` | Every XBRL fact the company has filed | `financial_facts` |
| `www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}` | The 10-K documents | Section extraction |

## Acquisition (`src/sectra/ingestion/`)

| Module | Responsibility | Key engineering decisions |
|---|---|---|
| `edgar_client.py` | All HTTP traffic to SEC | Declared `User-Agent` (SEC requirement) · throttled to **8 req/s** (limit is 10) · exponential backoff on 429/5xx/timeouts · **no retry on 403** (bad User-Agent or block: retrying only makes it worse) · writes to `<file>.part` then renames, so a crash never leaves a half-file that looks cached · the downloaded files *are* the cache |
| `company_resolver.py` | Ticker → zero-padded CIK | Rejects non-string tickers (PyYAML reads a bare `ON` as `True`) · reports all unknown tickers at once |
| `filing_downloader.py` | Choose and fetch 10-Ks | Converts SEC's columnar index to rows · **generator** over index pages, so older pages are fetched only when needed · exact form match (`10-K`, never `10-K/A`) · archive URLs use the unpadded CIK and the accession number without dashes |
| `download.py` | Orchestration + manifests | One failing company is logged and skipped; a 403 aborts the run · manifests drop companies removed from config · `filings.csv` stores a **SHA-256** per document |
| `dataset_report.py` | `docs/dataset.md` | Reports raw *and* deduplicated XBRL counts |

## On-disk layout (`data/`, git-ignored)

```text
data/
├── cache/company_tickers.json
├── raw/                                  # exactly what SEC sent; never modified
│   ├── submissions/CIK##########.json
│   ├── filings/<TICKER>/<period>_10-K_<accession>.htm
│   ├── xbrl/CIK##########.json
│   └── manifest/{companies.csv, filings.csv, last_run.json}
├── processed/                            # everything derived; rebuildable from raw/
│   ├── text/<TICKER>/<accession>.txt               full clean text
│   ├── sections/<TICKER>/<accession>/<item>.txt    one file per Item
│   ├── chunks/chunks.jsonl
│   └── embeddings/<model>__<dims>/{vectors.npy, chunk_ids.json, keys.json, cache_*}
└── logs/ask.jsonl                        # every question asked
```