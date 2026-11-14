# Evaluation

How retrieval quality was measured, what was tried, and what the numbers do and do not show.

**Status:** retrieval and the refusal threshold are measured. Answer faithfulness and the generator comparison are not done yet (see [Roadmap](roadmap.md)).

## Headline result

82 answerable questions, written in different words from the passage that answers them, searched across all 11,540 chunks with no filters:

| Retriever | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|---|---|---|---|---|
| Dense search | 57.3% | 84.1% | 90.2% | 0.682 |
| **Dense search + reranking (used by `ask`)** | **84.1%** | **95.1%** | **96.3%** | **0.890** |

Reranking found 9 questions in the top 5 that dense search missed and lost none (exact sign test, p = 0.004).

## The question sets

### How the questions were made

1. **Sample.** Five chunks per company, fixed seed: two from Item 1A, two from Item 7, one from the other Items. 19 companies have indexed text, giving 95 chunks.
2. **Generate.** An LLM (`gpt-oss-120b`) writes one question per chunk, the answer, and an **exact quote** from the chunk that contains the answer.
3. **Check by code.** The quote must appear in the chunk. 8 candidates failed and were dropped.
4. **Screen.** Each remaining candidate was screened by a second LLM; 5 were rejected. The author then read through the set.
5. **Label.** Gold = every chunk of the same filing that contains the quote. Neighbouring chunks overlap, so 2 of the 82 questions have two gold chunks. Because gold comes from the quote, it can be recomputed if chunking changes.
6. **Add unanswerable questions.** 15 questions in five categories that the corpus cannot answer.

| | Count |
|---|---|
| Candidates generated | 95 |
| Kept as answerable questions | **82** (Item 7: 34 · Item 1A: 32 · Item 1: 12 · Item 7A: 3 · Item 1C: 1; 19 companies) |
| Unanswerable questions | **15** (off-topic 5 · company not in corpus 3 · false premise 3 · year outside corpus 2 · advice or forecast 2) |

### Two versions of the same questions

| Set | File | Share of question words that also appear in the gold passage (median) |
|---|---|---|
| Original | `eval/datasets/retrieval_qa.jsonl` | 0.67 (15 questions at 0.8 or above) |
| **Paraphrased** | `eval/datasets/retrieval_qa_paraphrased.jsonl` | 0.16 (78 of 82 at 0.5 or below) |

An LLM that writes a question while looking at a passage reuses the passage's words. That makes keyword matching look far better than it is for a real user, who has not read the passage. The paraphrased set rewrites each question in different words and keeps the same gold chunks. It is the set reported as the headline; the original set is kept as the source and as evidence of the bias.

The paraphrases were written by the same model that wrote the original questions.

### Metrics

- A question counts as found at *k* if **any** of its gold chunks is in the top *k*.
- **Recall@1 / @5 / @10:** share of questions found. `ask` gives the model 5 passages, so Recall@5 is the one that decides whether the answer can be right.
- **MRR@10:** mean of 1/rank of the first gold chunk (0 if it is not in the top 10).
- **Two settings.** *Open*: no filters, every chunk is searched. *Scoped*: the question's ticker and fiscal year are passed as filters, which is what the agent will do from Phase 6.
- **Paired comparison.** Variants are compared question by question with an exact sign test on the questions where they differ.

## Results

### Current pipeline

| Question set | Setting | Retriever | R@1 | R@5 | R@10 | MRR@10 |
|---|---|---|---|---|---|---|
| Paraphrased | open | dense | 57.3% | 84.1% | 90.2% | 0.682 |
| Paraphrased | open | rerank | 84.1% | 95.1% | 96.3% | 0.890 |
| Paraphrased | scoped | dense | 61.0% | 90.2% | 96.3% | 0.727 |
| Paraphrased | scoped | rerank | 86.6% | 98.8% | 100.0% | 0.920 |
| Original | open | dense | 78.0% | 95.1% | 97.6% | 0.852 |
| Original | open | rerank | 91.5% | 100.0% | 100.0% | 0.949 |
| Original | scoped | dense | 81.7% | 98.8% | 98.8% | 0.890 |
| Original | scoped | rerank | 91.5% | 100.0% | 100.0% | 0.951 |

- **The reranker is limited by its candidates, not by its ranking.** On the paraphrased set the gold chunk is among the 60 candidates for 97.6% of questions (100% when scoped), and the reranker places it in the top 5 for 95.1%.
- **All four remaining misses are "right filing, wrong passage".** The system finds the right document and picks a neighbouring passage.
- **The original set is saturated** at 100% and can no longer tell variants apart.

### What was tried

Recall@5 on the paraphrased set, open setting. Every number is in [`eval/results/experiments.md`](../eval/results/experiments.md).

| Step | Dense | BM25 | Hybrid (RRF) | Rerank | Candidate pool |
|---|---|---|---|---|---|
| Local `bge-base` embeddings, 768-d | 24.4% | 22.0% | 35.4% | 64.6% | 64.6% |
| Hosted 8B embedding model, 1,024-d | 84.1% | 22.0% | 61.0% | 96.3% | 97.6% |
| BM25 and hybrid removed; rerank over 60 dense candidates | 84.1% | | | 95.1% | 97.6% |

1. **Dense baseline with a small local model:** 50.0% on the original set, 24.4% once the questions were paraphrased.
2. **BM25** (own implementation) scored 82.9% on the original set and looked like the best single retriever. On the paraphrased set it fell to 22.0%. Its lead was the wording bias.
3. **Hybrid search** (reciprocal rank fusion of dense and BM25) helped while both were weak (35.4% vs 24.4%, p = 0.022).
4. **Reranking** the 60 hybrid candidates raised Recall@5 to 64.6%, exactly the share of questions whose gold chunk was among the candidates. The candidates were the bottleneck.
5. **A stronger embedding model** raised dense search from 24.4% to 84.1% and candidate recall to 97.6%.
6. **Hybrid then became harmful as a ranking.** Equal-weight fusion let the weak BM25 list pull the strong dense list down (61.0% vs 84.1%, p < 0.001).
7. **BM25 removed.** Reranking 60 dense candidates gives the same candidate recall (97.6%) as the hybrid pool, and Recall@5 differs by one question (95.1% vs 96.3%). The simpler pipeline was kept.

## Refusal threshold

`python -m sectra.evaluation.threshold` reads the saved results and, for each possible threshold on the top-1 score, counts the unanswerable questions stopped and the answerable ones wrongly refused. A refusal counts as a loss only if the gold passage was in the top 5.

Reranker scores, open setting:

| Threshold | Unanswerable stopped (of 15) | Answerable lost, paraphrased (of 82) |
|---|---|---|
| **0.042 (chosen)** | **5** | **0** |
| 0.0472 | 7 | 2 (2.4%) |
| 0.0505 | 10 | 2 (2.4%) |
| 0.0568 | 12 | 6 (7.3%) |
| 0.0601 | 13 | 8 (9.8%) |
| 0.0780 | 15 | 26 (31.7%) |

- **Chosen values:** `rerank: 0.042`, `dense: 0.40`, set slightly below the highest threshold that loses no answerable question, because they were tuned on the same questions they are tested on.
- **The score gate is a cost saver, not a safety mechanism.** It stops a third of the unanswerable questions. The rest retrieve passages that look related: Tesla supply-chain risks score higher than some real questions, because other companies' supply-chain passages are a good semantic match.
- **Reranker scores separate better than dense scores.** For a 2.4% loss the reranker stops 10 of 15; dense search stops 7–8 for a 3.7% loss.
- **Two categories have an exact fix.** "Company not in corpus" and "year outside corpus" can be checked against the filing manifest once the company and year are extracted from the question. That is the router's job in Phase 6.

The questions that pass the gate are left to the model's `NOT_FOUND` rule. How often that works is part of the faithfulness evaluation, which is not done yet.

## What these numbers do not show

- **The questions are easy in kind.** Each was written from one chunk and has one right passage. Vague questions, comparisons across companies or years, and questions that need several passages are not measured.
- **82 questions.** A difference of one question is 1.2 points. The jump from the embedding change is far outside noise; 95.1% vs 96.3% is not a difference.
- **The questions were written, paraphrased and screened by LLMs** and read through, not written, by a person.
- **Thresholds are tuned and tested on the same set.**
- **Retrieval is not answer quality.** Whether the generated answers are supported by their cited passages has not been measured.
- **Hosted APIs filter content.** A few passages per run are refused by a content-safety filter and scored 0.

## Reproducing

```bash
make eval         # dense and rerank on both question sets, with paired comparisons
make threshold    # threshold sweep for both retrievers
```

Results are written per question to `eval/results/retrieval_<variant>[_paraphrased].json`. Rebuilding the question sets: `python -m sectra.evaluation.qa_set generate | review | build | paraphrase`.