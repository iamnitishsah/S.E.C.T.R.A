from dotenv import load_dotenv

from sectra.retrieval.dense import DenseRetriever

load_dotenv()
r = DenseRetriever()
TESTS = [
    ("climate change laws and greenhouse gas emission regulation", {}),
    ("climate change laws and greenhouse gas emission regulation", {"fiscal_year": 2025}),
    ("what drove the increase in data center revenue", {"ticker": "NVDA", "item_code": "7", "fiscal_year": 2026}),
    ("supply chain and manufacturing risks", {"ticker": "amd", "fiscal_year": "2025", "item_code": "1A"}),
]
for q, f in TESTS:
    print(f"\n{q}  {f}")
    for h in r.search_filings(q, **f):
        print(f"  {h['score']:.3f}  {h['chunk_id']:32}  {h['header'][:70]}")