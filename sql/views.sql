-- Derived views over financial_facts. Re-runnable: CREATE OR REPLACE.

-- One row per 10-K: its year-end and SEC's fy label (used only as a hint).
CREATE OR REPLACE VIEW fiscal_year_ends AS
SELECT cik, accession_no,
       MAX(filing_fy)  AS sec_fy,
       MAX(period_end) AS fy_end
FROM financial_facts
WHERE form = '10-K'
  AND filing_fp = 'FY'
  AND taxonomy = 'us-gaap'
  AND period_start IS NOT NULL
  AND DATEDIFF(period_end, period_start) BETWEEN 350 AND 380
GROUP BY cik, accession_no;

-- Each company's labelling convention: the most common (SEC fy - calendar year).
-- Taking the most common value means a few wrong fy labels are outvoted.
CREATE OR REPLACE VIEW fiscal_year_offsets AS
SELECT cik, offset_years
FROM (
         SELECT cik, CAST(sec_fy AS SIGNED) - CAST(YEAR(DATE_SUB(fy_end, INTERVAL 7 DAY)) AS SIGNED) AS offset_years,
     ROW_NUMBER() OVER (PARTITION BY cik ORDER BY COUNT(*) DESC) AS rn
FROM fiscal_year_ends
GROUP BY cik, offset_years
    ) t
WHERE rn = 1;

-- One row per company fiscal year, label derived from the year-end date.
-- 7-day shift: 52/53-week years ending Jan 1-3 belong to the previous fiscal year.
CREATE OR REPLACE VIEW fiscal_years AS
SELECT e.cik, e.fy_end,
    CAST(YEAR(DATE_SUB(e.fy_end, INTERVAL 7 DAY)) AS SIGNED) + o.offset_years AS fiscal_year,
    MAX(e.sec_fy) AS sec_fy,    -- kept for auditing disagreements
    COUNT(*)      AS n_filings
FROM fiscal_year_ends e
    JOIN fiscal_year_offsets o USING (cik)
GROUP BY e.cik, e.fy_end, o.offset_years;

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