# Retrieval experiments (archived numbers)

Every retrieval variant measured in Phase 4, including the ones later removed from the code
(BM25, hybrid RRF fusion, and reranking over the hybrid candidate pool). 82 answerable questions per set.
`pool` is the share of questions whose gold chunk was among the reranker's candidates.

| Embedder | Question set | Setting | Variant | R@1 | R@5 | R@10 | MRR@10 | pool |
|---|---|---|---|---|---|---|---|---|
| bge-base-en-v1.5 (768-d, local) | original | open | dense | 28.0% | 50.0% | 62.2% | 0.376 |  |
| bge-base-en-v1.5 (768-d, local) | original | scoped | dense | 47.6% | 76.8% | 87.8% | 0.602 |  |
| bge-base-en-v1.5 (768-d, local) | original | open | bm25 | 53.7% | 82.9% | 91.5% | 0.656 |  |
| bge-base-en-v1.5 (768-d, local) | original | scoped | bm25 | 75.6% | 96.3% | 97.6% | 0.838 |  |
| bge-base-en-v1.5 (768-d, local) | original | open | hybrid (RRF of dense + BM25) | 41.5% | 75.6% | 87.8% | 0.559 |  |
| bge-base-en-v1.5 (768-d, local) | original | scoped | hybrid (RRF of dense + BM25) | 63.4% | 90.2% | 96.3% | 0.748 |  |
| bge-base-en-v1.5 (768-d, local) | original | open | rerank over hybrid pool (30 dense + 30 BM25) | 87.8% | 95.1% | 95.1% | 0.909 | 95.1% |
| bge-base-en-v1.5 (768-d, local) | original | scoped | rerank over hybrid pool (30 dense + 30 BM25) | 91.5% | 100.0% | 100.0% | 0.951 | 100.0% |
| bge-base-en-v1.5 (768-d, local) | paraphrased | open | dense | 14.6% | 24.4% | 32.9% | 0.186 |  |
| bge-base-en-v1.5 (768-d, local) | paraphrased | scoped | dense | 23.2% | 43.9% | 64.6% | 0.325 |  |
| bge-base-en-v1.5 (768-d, local) | paraphrased | open | bm25 | 11.0% | 22.0% | 31.7% | 0.156 |  |
| bge-base-en-v1.5 (768-d, local) | paraphrased | scoped | bm25 | 23.2% | 50.0% | 62.2% | 0.342 |  |
| bge-base-en-v1.5 (768-d, local) | paraphrased | open | hybrid (RRF of dense + BM25) | 14.6% | 35.4% | 42.7% | 0.234 |  |
| bge-base-en-v1.5 (768-d, local) | paraphrased | scoped | hybrid (RRF of dense + BM25) | 26.8% | 59.8% | 72.0% | 0.397 |  |
| bge-base-en-v1.5 (768-d, local) | paraphrased | open | rerank over hybrid pool (30 dense + 30 BM25) | 59.8% | 64.6% | 64.6% | 0.618 | 64.6% |
| bge-base-en-v1.5 (768-d, local) | paraphrased | scoped | rerank over hybrid pool (30 dense + 30 BM25) | 82.9% | 91.5% | 92.7% | 0.869 | 92.7% |
| nemotron-3.5-embed-8b (1024-d, API) | original | open | dense | 78.0% | 95.1% | 97.6% | 0.852 |  |
| nemotron-3.5-embed-8b (1024-d, API) | original | scoped | dense | 81.7% | 98.8% | 98.8% | 0.890 |  |
| nemotron-3.5-embed-8b (1024-d, API) | original | open | bm25 | 53.7% | 82.9% | 91.5% | 0.656 |  |
| nemotron-3.5-embed-8b (1024-d, API) | original | scoped | bm25 | 75.6% | 96.3% | 97.6% | 0.838 |  |
| nemotron-3.5-embed-8b (1024-d, API) | original | open | hybrid (RRF of dense + BM25) | 69.5% | 92.7% | 96.3% | 0.800 |  |
| nemotron-3.5-embed-8b (1024-d, API) | original | scoped | hybrid (RRF of dense + BM25) | 82.9% | 97.6% | 100.0% | 0.892 |  |
| nemotron-3.5-embed-8b (1024-d, API) | original | open | rerank over hybrid pool (30 dense + 30 BM25) | 91.5% | 100.0% | 100.0% | 0.949 | 100.0% |
| nemotron-3.5-embed-8b (1024-d, API) | original | scoped | rerank over hybrid pool (30 dense + 30 BM25) | 91.5% | 100.0% | 100.0% | 0.951 | 100.0% |
| nemotron-3.5-embed-8b (1024-d, API) | paraphrased | open | dense | 57.3% | 84.1% | 90.2% | 0.682 |  |
| nemotron-3.5-embed-8b (1024-d, API) | paraphrased | scoped | dense | 61.0% | 90.2% | 96.3% | 0.727 |  |
| nemotron-3.5-embed-8b (1024-d, API) | paraphrased | open | bm25 | 11.0% | 22.0% | 31.7% | 0.156 |  |
| nemotron-3.5-embed-8b (1024-d, API) | paraphrased | scoped | bm25 | 23.2% | 50.0% | 62.2% | 0.342 |  |
| nemotron-3.5-embed-8b (1024-d, API) | paraphrased | open | hybrid (RRF of dense + BM25) | 32.9% | 61.0% | 81.7% | 0.450 |  |
| nemotron-3.5-embed-8b (1024-d, API) | paraphrased | scoped | hybrid (RRF of dense + BM25) | 35.4% | 70.7% | 84.1% | 0.504 |  |
| nemotron-3.5-embed-8b (1024-d, API) | paraphrased | open | rerank over hybrid pool (30 dense + 30 BM25) | 85.4% | 96.3% | 97.6% | 0.902 | 97.6% |
| nemotron-3.5-embed-8b (1024-d, API) | paraphrased | scoped | rerank over hybrid pool (30 dense + 30 BM25) | 86.6% | 98.8% | 100.0% | 0.921 | 100.0% |

BM25 does not use the embedder, so its rows are identical under both.
