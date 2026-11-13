# Phase 1 validation: XBRL metrics vs. source 10-K filings

**Status:** manual spot checks done (10 values, 4 companies); automated cross-check of all
filings pending (see the end of this document).

## Method

Values from `financial_metrics` were compared by hand with the consolidated financial
statements (Item 8) in the downloaded 10-K documents. Values are in $ millions unless noted.
Printed statements use scale labels ("in millions", "shares in thousands"); XBRL stores full
values, so the comparison accounts for scale.

## Manual spot checks

| Ticker | Metric | FY | DB value | Printed value | Statement / line | Result |
|---|---|---|---|---|---|---|
| AAPL | revenue | 2026 | 478,834 | 478,834 | Statement of Operations / Total net sales | ✅ |
| AAPL | revenue | 2025 | 416,161 | 416,161 | Statement of Operations / Total net sales | ✅ |
| AAPL | revenue | 2024 | 391,035 | 391,035 | Statement of Operations / Total net sales | ✅ |
| AAPL | net_income | 2025 | 112,010 | 112,010 | Statement of Operations / Net income | ✅ |
| AMZN | operating_cash_flow | 2025 | 139,514 | 139,514 | Cash Flows / Net cash provided by operating activities | ✅ |
| CVX | revenue | 2025 | 184,432 | 184,432 | Income / Sales and other operating revenues | ✅ after fix (was 189,031) |
| COP | revenue | 2025 | 58,944 | 58,944 | Income / Sales and other operating revenues | ✅ |
| COP | net_income | 2025 | 7,988 | 7,988 | Income / Net income | ✅ |
| COP | eps_diluted | 2025 | 6.35 | 6.35 | Income / Diluted EPS ($) | ✅ |
| COP | shares_diluted | 2025 | 1,253,446,000 | 1,253,446 (thousands) | Income / Diluted weighted-average shares | ✅ |

## Finding: the same XBRL tag means different lines at different companies

| Company | `us-gaap:Revenues` holds | Correct revenue tag |
|---|---|---|
| Chevron (CVX) | **Total revenues and other income** = 184,432 sales + 3,000 equity-affiliate income + 1,599 other income = 189,031 | `RevenueFromContractWithCustomerExcludingAssessedTax` |
| ConocoPhillips (COP) | Sales and other operating revenues = 58,944 | `Revenues` |

A single global tag priority cannot be trusted without per-company checks. Fixed with a
company-specific override in `sql/metric_map.csv` (`cik = 0000093410`).

**Method used to find the right tag:** read the value off the printed statement, then search
`annual_facts` for the tag holding that exact value.

## Decisions

- **Revenue definition:** sales from operations, excluding equity-affiliate income and other income.
- **Fiscal year:** derived as `YEAR(year-end − 7 days) + company offset`, not taken from SEC's `fy`.
- **Duplicates:** when a period is reported in several filings, the latest filing wins (captures restatements).
- **Missing lines stay NULL:** no derived or estimated values in `financial_metrics`.

## FY2025 coverage (companies out of 20)

| Metric | Companies | | Metric | Companies |
|---|---|---|---|---|
| revenue | 20 | | cash | 18 |
| net_income | 20 | | cost_of_revenue | 18 |
| eps_basic / eps_diluted | 20 | | capex | 17 |
| shares_diluted | 20 | | rnd_expense | 17 |
| total_assets | 20 | | operating_income | 13 |
| total_equity | 20 | | total_liabilities | 13 |
| operating_cash_flow | 20 | | gross_profit | 7 |

Gaps reflect what companies report (e.g., pharma and energy companies present no gross profit line).

## Known limitations

- **SEC `fy` field is unreliable:** wrong for NVIDIA FY2011–FY2014 (one year early). Fiscal year is derived from period dates instead.
- **Missing fiscal years before 2017:** INTC 2010, LLY 2010–2011, EOG 2013, COP 2015. Queries for these return "not found".
- **Stock splits:** per-share values and share counts are not split-adjusted across history (Apple 7:1 in 2014, 4:1 in 2020). Compare totals, or per-share values within one filing.
- **No segment data:** SEC's companyfacts API contains only consolidated (non-dimensional) facts. Segment questions must be answered from filing text (RAG).
- **Ticker ≠ identity:** after Exxon Mobil's 2026 reorganization, `XOM` points to a new CIK with no 10-K history. MPC used instead.
- **Not yet verified by hand:** NVDA revenue, MSFT operating income, GOOGL EPS, INTC net income (minority interests), JNJ net income, LLY R&D, META capex, MPC total assets, PFE revenue, EOG revenue (may include derivative and asset-sale gains).

## Pending: automated cross-check

Planned `make validate`: parse the inline XBRL in each downloaded 10-K, compare every
`financial_metrics` value with the tagged value for that filing's own fiscal year
(match / restated / mismatch / missing), and output the printed row label for each metric
so tag *meaning* can be reviewed in one table.