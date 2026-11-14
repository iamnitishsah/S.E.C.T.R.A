from sectra.evaluation.threshold import suggest, sweep


def row(score, rank=1, kind="generated"):
    return {"type": kind, "top1_score": score, "rank": rank}


def test_sweep_counts_stopped_and_lost():
    ans = {"paraphrased": [row(0.30), row(0.10), row(0.04, rank=None)]}
    unans = [row(0.05, kind="unanswerable"), row(0.20, kind="unanswerable")]
    table = sweep(ans, unans)
    assert [t["threshold"] for t in table] == [0.0, 0.0501, 0.2001]
    assert [t["stopped"] for t in table] == [0, 1, 2]
    # the 0.04 question had no gold passage retrieved, so refusing it is not a loss
    assert [t["lost"]["paraphrased"] for t in table] == [0, 0, 1]
    assert suggest(table, 3, "paraphrased", max_loss=0.0) == 0.0501