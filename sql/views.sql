-- Derived views over financial_facts. Re-runnable: CREATE OR REPLACE.

-- One row per company fiscal year: when it ends and what the company calls it.
-- A 10-K's own fiscal year is filing_fy, and its year-end is the latest end
-- date of its ~1-year us-gaap facts. (Cover-page dei facts are excluded because
-- their dates fall after year-end.)
CREATE OR REPLACE VIEW fiscal_years AS
SELECT cik, fy_end, MAX(fiscal_year) AS fiscal_year, COUNT(*) AS n_filings
FROM (
         SELECT cik, accession_no,
                MAX(filing_fy)  AS fiscal_year,
                MAX(period_end) AS fy_end
         FROM financial_facts
         WHERE form = '10-K'
           AND filing_fp = 'FY'
           AND taxonomy = 'us-gaap'
           AND period_start IS NOT NULL
           AND DATEDIFF(period_end, period_start) BETWEEN 350 AND 380
         GROUP BY cik, accession_no
     ) per_filing
GROUP BY cik, fy_end;

-- One value per company, concept, unit and fiscal year.
-- Annual durations (income/cash-flow items) and year-end instants (balance sheet).
-- When the same period is reported several times, the latest filing wins,
-- so restatements replace original figures. Same rule SEC uses for frames.
CREATE OR REPLACE VIEW annual_facts AS
WITH ranked AS (
    SELECT f.*,
           ROW_NUMBER() OVER (
               PARTITION BY f.cik, f.taxonomy, f.tag, f.unit, f.period_start, f.period_end
               ORDER BY f.filed_date DESC, f.accession_no DESC
           ) AS rn
    FROM financial_facts f
    WHERE f.form IN ('10-K', '10-K/A')
      AND (f.period_start IS NULL
           OR DATEDIFF(f.period_end, f.period_start) BETWEEN 350 AND 380)
)
SELECT r.cik, y.fiscal_year, r.taxonomy, r.tag, r.unit, r.value,
       r.period_start, r.period_end,
       CASE WHEN r.period_start IS NULL THEN 'instant' ELSE 'duration' END AS period_type,
       r.accession_no AS source_accession, r.filed_date
FROM ranked r
         JOIN fiscal_years y ON y.cik = r.cik AND y.fy_end = r.period_end
WHERE r.rn = 1;