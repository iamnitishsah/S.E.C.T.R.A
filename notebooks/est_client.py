import os, logging
from pathlib import Path
from dotenv import load_dotenv
from sectra.ingestion.edgar_client import EdgarClient

logging.basicConfig(level=logging.INFO)
load_dotenv()
c = EdgarClient(os.environ["SEC_USER_AGENT"])
d = c.fetch_json("https://www.sec.gov/files/company_tickers.json",
                 Path("data/cache/company_tickers.json"))
print(len(d), "companies | network calls:", c.network_calls)