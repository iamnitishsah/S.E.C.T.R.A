# Findings and decisions

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

## SQL Analyst

| Finding | Evidence | Handling |
|---|---|---|
| A model guesses tickers it is not given | "Chevron" became `COP` (ConocoPhillips) when the schema listed tickers only | Company names shown next to tickers in the schema text |
| "Fiscal 2025" is a different period for each company | NVIDIA's fiscal 2025 ended in January 2025, AMD's in December 2025; a cross-company growth ranking compares periods almost a year apart | Values are correct as filed; the writer should state `period_end` when year-ends differ (Phase 6) |
| The cited filing can be a later year's 10-K | NVIDIA's fiscal 2025 revenue cites the fiscal 2026 filing, because the latest filing wins and it restates the prior year | By design (restatements replace originals); noted so a reader is not surprised |
| A stated default is not a rule | The default fiscal year was in the schema text, and the model still returned every year | Explicit rule in the prompt |
| A gold query can ask for more than the question | One gold query required a growth percentage for "which companies had lower revenue" | Gold corrected; first-run score reported both ways |
| A sign can hide a correct number | "fell by 3.9%" was flagged because the row holds −3.9 | The number check compares absolute values |
| A warning fired on the model's own `LIMIT` | "Row limit reached" appeared for `LIMIT 1` | Only the cap imposed by the validator counts |

## Research graph

| Finding | Evidence | Handling |
|---|---|---|
| A router can refuse what a similarity score cannot | Company-not-indexed and year-not-indexed questions passed the Phase 4 score gate; the corpus check refuses all of them | Deterministic check against the catalog before any retrieval |
| No single layer catches every unanswerable question | Of 15: router 8, evidence check 4, writer 3 | Three layers kept |
| The router over-uses the hybrid route | Six sector-level rankings ("which technology company had the largest total assets") went to `both` | Prompt rule added; not re-measured |
| A subsidiary name is read as an unknown company | "MPLX" (owned by Marathon Petroleum) was refused as not indexed | Alias added; the general case remains |
| A stray list item in YAML became a `None` table name | `configs/sql.yaml` gained a lone `-`; the validator crashed on it | Empty items ignored when the config is loaded |
| Models cite at the end of a bullet, not after every sentence | Four of five bullets were flagged as uncited | A citation covers the sentences before it in the same bullet |
| Citation markers were read as figures | `[2]` and `[3]` flagged as numbers not in the evidence | Citations removed before the number check |
| `gpt-oss` writes `【T】` for `[T]` | Table citations were not recognised | Normalized like `【1】` |

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
| Deterministic ratio tools in Python | Dropped: ratios and growth are computed in SQL | The goal was that the model never does arithmetic, and SQL already guarantees it |
| RAGAS for faithfulness | Custom claim-level judge (pending) | Fewer dependencies, and the judging rules stay readable |
| Hand-labelled retrieval questions | LLM-generated with a verifiable quote, LLM-screened, read through by hand | Labels can be recomputed if chunking changes |
| 50–100 companies, 10-Qs, banks | 20 companies in 4 sectors, 10-K only | Banks need different revenue concepts in the metric map |
| Item 8 indexed for retrieval | Not indexed | Financial figures come from XBRL |