-- S.E.C.T.R.A relational schema (MySQL 8.4)

CREATE TABLE IF NOT EXISTS companies (
    cik              CHAR(10)     NOT NULL,   -- zero-padded SEC id: the real identity (tickers changes)
    ticker           VARCHAR(10)  NOT NULL,
    name             VARCHAR(255) NOT NULL,
    sector           VARCHAR(50)  NOT NULL,   -- our grouping, from configs/companies.yaml
    sic              CHAR(4)      NULL,       -- SEC industry code
    sic_description  VARCHAR(255) NULL,
    exchange         VARCHAR(20)  NULL,
    fiscal_year_end  CHAR(4)      NULL,       -- MMDD, e.g. '0927' for Apple
    PRIMARY KEY (cik),
    UNIQUE KEY uq_companies_ticker (ticker)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS filings (
    accession_no      CHAR(20)      NOT NULL, -- e.g. 0000320193-24-000123
    cik               CHAR(10)      NOT NULL,
    form_type         VARCHAR(20)   NOT NULL,
    filing_date       DATE          NOT NULL,
    period_of_report  DATE          NOT NULL,
    fiscal_year       SMALLINT      NULL,     -- filled from XBRL in step 1.3, not guessed from the date
    primary_document  VARCHAR(255)  NOT NULL,
    primary_doc_url   VARCHAR(500)  NOT NULL,
    local_path        VARCHAR(500)  NOT NULL,
    size_bytes        INT UNSIGNED  NOT NULL,
    sha256            CHAR(64)      NOT NULL,
    is_inline_xbrl    BOOLEAN       NOT NULL DEFAULT FALSE,
    PRIMARY KEY (accession_no),
    KEY ix_filings_cik_period (cik, period_of_report),
    CONSTRAINT fk_filings_company FOREIGN KEY (cik) REFERENCES companies (cik)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS financial_facts (
    fact_id       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    cik           CHAR(10)       NOT NULL,
    taxonomy      VARCHAR(20)    NOT NULL,   -- us-gaap, dei, srt, ...
    tag           VARCHAR(255)   NOT NULL,   -- e.g. Revenues, NetIncomeLoss
    unit          VARCHAR(50)    NOT NULL,   -- USD, shares, USD/shares, pure
    value         DECIMAL(30,6)  NOT NULL,   -- exact decimal, never FLOAT for money
    period_start  DATE           NULL,       -- NULL = instant fact (balance sheet "as of" a date)
    period_end    DATE           NOT NULL,
    filing_fy     SMALLINT       NULL,       -- fiscal year of the FILING that reported it, NOT of the fact
    filing_fp     VARCHAR(4)     NULL,       -- FY / Q1 / Q2 / Q3, also of the filing
    form          VARCHAR(20)    NOT NULL,   -- 10-K, 10-Q, 8-K, ...
    accession_no  CHAR(20)       NOT NULL,   -- no FK: most facts come from filings we didn't download
    filed_date    DATE           NOT NULL,
    frame         VARCHAR(20)    NULL,       -- CY2024 / CY2024Q3 / CY2024Q4I: SEC's one pick per period
    PRIMARY KEY (fact_id),
    KEY ix_facts_lookup (cik, tag, period_end),
    KEY ix_facts_frame (cik, tag, frame),
    CONSTRAINT fk_facts_company FOREIGN KEY (cik) REFERENCES companies (cik)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE IF NOT EXISTS metric_map (
    canonical_metric VARCHAR(50)  NOT NULL,              -- the name the agent uses: revenue, net_income...
    taxonomy         VARCHAR(20)  NOT NULL DEFAULT 'us-gaap',
    tag              VARCHAR(255) NOT NULL,
    unit             VARCHAR(50)  NOT NULL,
    period_type      ENUM('duration', 'instant') NOT NULL,
    priority         TINYINT UNSIGNED NOT NULL,          -- 1 = try first
    cik              CHAR(10)     NOT NULL DEFAULT '',   -- '' = all companies; set = override for one company
    PRIMARY KEY (canonical_metric, cik, priority)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE IF NOT EXISTS filing_sections (
    accession_no  CHAR(20)      NOT NULL,
    item_code     VARCHAR(3)    NOT NULL,              -- 1, 1A, 7, 7A ...
    heading       VARCHAR(255)  NOT NULL,              -- heading line as found, for review
    char_start    INT UNSIGNED  NOT NULL,              -- offsets into the full-text file
    char_end      INT UNSIGNED  NOT NULL,
    n_chars       INT UNSIGNED  NOT NULL,
    method        ENUM('toc_link', 'heading') NOT NULL,
    quality       ENUM('ok', 'suspect')       NOT NULL,  -- length outside plausible range -> suspect
    text_path     VARCHAR(500)  NOT NULL,
    PRIMARY KEY (accession_no, item_code),             -- natural key: stable across rebuilds
    CONSTRAINT fk_sections_filing FOREIGN KEY (accession_no) REFERENCES filings (accession_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;