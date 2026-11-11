UPDATE filings f
    JOIN fiscal_years y ON y.cik = f.cik AND y.fy_end = f.period_of_report
    SET f.fiscal_year = y.fiscal_year;

-- Materialize financial_metrics from the view: ms queries instead of seconds.
-- Build into a new table, then swap atomically, so readers never see it missing or half-built.
DROP TABLE IF EXISTS financial_metrics_new;
CREATE TABLE financial_metrics_new (
                                       cik              CHAR(10)      NOT NULL,
                                       ticker           VARCHAR(10)   NOT NULL,
                                       sector           VARCHAR(50)   NOT NULL,
                                       fiscal_year      SMALLINT      NOT NULL,
                                       fiscal_period    CHAR(2)       NOT NULL,
                                       canonical_metric VARCHAR(50)   NOT NULL,
                                       value            DECIMAL(30,6) NOT NULL,
                                       unit             VARCHAR(50)   NOT NULL,
                                       source_tag       VARCHAR(255)  NOT NULL,
                                       period_end       DATE          NOT NULL,
                                       source_accession CHAR(20)      NOT NULL,
                                       PRIMARY KEY (cik, fiscal_year, canonical_metric),          -- also proves: one value per key
                                       KEY ix_fm_ticker (ticker, canonical_metric, fiscal_year),
                                       KEY ix_fm_metric_year (canonical_metric, fiscal_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO financial_metrics_new SELECT * FROM financial_metrics_v;

CREATE TABLE IF NOT EXISTS financial_metrics LIKE financial_metrics_new;  -- first run only
RENAME TABLE financial_metrics TO financial_metrics_old,
             financial_metrics_new TO financial_metrics;
DROP TABLE financial_metrics_old;