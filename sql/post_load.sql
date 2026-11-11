UPDATE filings f
    JOIN fiscal_years y ON y.cik = f.cik AND y.fy_end = f.period_of_report
    SET f.fiscal_year = y.fiscal_year;