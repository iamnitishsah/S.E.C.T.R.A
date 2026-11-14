# Findings and decisions

[← README](../README.md) · [Data acquisition](01-data-acquisition.md) · [Financial database](02-financial-database.md) · [Filing text](03-filing-text.md) · [Retrieval and answers](04-retrieval-and-answers.md) · [Evaluation](05-evaluation.md) · [Findings](findings.md) · [Roadmap](roadmap.md)

Problems found while building, each with its evidence and how it is handled, followed by the places where the plan changed.

## Data and the financial database

| Finding | Evidence | Handling |
|---|---|---|
| Tickers are not stable identities | After Exxon Mobil's July 2026 reorganization, `XOM` maps to a new holding-company CIK with no 10-K history | CIK is the key; MPC used in the starter set |
| SEC's `fy` field can be wrong | NVIDIA FY2011–2014 labelled one year early | Fiscal year derived from period dates |
| Same tag, different meaning | Chevron vs. ConocoPhillips `Revenues` | Per-company override; validation against printed statements |
| Stock splits break per-share history | Apple shares ×7 (2014), ×4 (2020) | Compare totals; split-adjustment is future work |
| No segment data in companyfacts | Only consolidated facts | Segment questions go to the text (tables in MD&A) |
| MySQL `YEAR()` is unsigned | A view failed only on first use, on NVIDIA's negative offset | Cast to signed; every view change is followed by a query that uses it |

## Retrieval and answers

| Finding | Evidence | Handling |
|---|---|---|
| Copies across years crowd retrieval | "Climate regulation" returned 5/5 ConocoPhillips chunks from different years; with a year filter, 4/5 | Year filters now; per-company grouping with the router in Phase 6 |
| Similarity threshold was a guess | A nonsense question passed `min_score: 0.5` (the model refused it instead) | Calibrated per retriever on answerable vs. unanswerable questions |
| Model-specific citation styles | gpt-oss wrote `【1†L1-L3】`, so every sentence looked uncited | Normalize before validating |
| Reasoning tokens consume the output budget | An answer was cut off at exactly `max_tokens` | Truncation detection; larger limit |
| Plausible but unfaithful paraphrase | A Merck answer added its own interpretation of "entities that negotiate drug prices" | Faithfulness evaluation (Phase 4, pending) |
| A weak embedding model was the bottleneck | Reranking could not exceed 64.6% Recall@5 because the gold chunk was among the candidates for only 64.6% of questions | Embedding model replaced; candidate recall rose to 97.6% |
| Fusing a weak ranking with a strong one hurts | After the embedding change, hybrid search (RRF of dense and BM25) scored 61.0% against 84.1% for dense alone | BM25 and hybrid removed; the reranker re-sorts dense candidates |
| A similarity score cannot tell that a company is not indexed | "What supply chain risks did Tesla describe?" scores higher than some answerable questions | Score gate kept only as a cost saver; the model's `NOT_FOUND` rule is the second layer; manifest check planned with the router |
| Hosted APIs reject a whole batch for one passage | `422 input rejected by content safety screening` at question 15 of 97 | Split the batch until the passage is isolated; score it 0 (reranker) or embed its header only (embedder); count it |
| The citation checker split sentences at "U.S." | A fully cited NVIDIA answer was reported with 4 uncited sentences | Sentence splitter skips known abbreviations |

## Evaluation

| Finding | Evidence | Handling |
|---|---|---|
| LLM-written questions copy the passage's wording | Median word overlap 0.67; BM25 scored 82.9% on them and 22.0% on paraphrases of the same questions | Paraphrased set (median overlap 0.16) is the headline set |
| The quote checker rejected correct quotes | 13 of 21 "invalid" candidates were valid: the model wrote non-breaking hyphens (U+2011) and added a full stop | Normalize all Unicode hyphens, strip trailing punctuation; candidates recovered |
| A saturated test set stops being useful | Reranked retrieval reaches 100% Recall@5 on the original questions | Kept as the source of the paraphrased set, not as the headline |
| pytest collected a scratch script | `notebooks/fd_test.py` calls the SEC API at import time | `testpaths = ["tests"]`; scratch scripts untracked |

## Changes to the original plan

| Planned | What happened | Why |
|---|---|---|
| A local LLM as one generation backend | Hosted models only | An 8B model does not fit next to Docker on an 8 GB machine. The open-vs-closed comparison uses hosted open-weight and closed models |
| Separate API and local LLM clients | One OpenAI-compatible client for every provider | A new provider is a config entry |
| Embedding model fixed (`bge-base-en-v1.5`, local) | Replaced by a hosted 8B embedding model | Largest measured gain: dense Recall@5 24.4% → 84.1% on paraphrased questions |
| BM25 + hybrid search as the retrieval upgrade | Built, measured, removed | No measurable benefit once the embedder was strong; see [Evaluation](05-evaluation.md#what-was-tried) |
| Local cross-encoder reranker | Hosted reranking API | Same reason as the LLM: memory |
| RAGAS for faithfulness | Custom claim-level judge (pending) | Fewer dependencies, and the judging rules stay readable |
| Hand-labelled retrieval questions | LLM-generated with a verifiable quote, LLM-screened, read through by hand | Labels can be recomputed if chunking changes |
| 50–100 companies, 10-Qs, banks | 20 companies in 4 sectors, 10-K only | Banks need different revenue concepts in the metric map |
| Item 8 indexed for retrieval | Not indexed | Financial figures come from XBRL |