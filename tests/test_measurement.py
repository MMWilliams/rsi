import math

import pytest

from rsi.neural import pass_at_k, raw_scores


@pytest.mark.parametrize("n,c,k", [(4, 1, 2), (10, 3, 4), (64, 5, 8), (64, 0, 64), (64, 64, 1)])
def test_pass_at_k_matches_exact_without_replacement_probability(n, c, k):
    expected = 1 - (math.comb(n - c, k) / math.comb(n, k) if n - c >= k else 0)
    assert pass_at_k(n, c, k) == pytest.approx(expected)


def test_large_k_cannot_exceed_sample_count():
    with pytest.raises(ValueError):
        pass_at_k(8, 2, 64)


def test_visible_fit_does_not_count_as_hidden_correctness():
    task = {"id": "t", "visible": [["John Lee", "John"]], "hidden": [["Alexandria Wu", "Alexandria"]]}
    samples = {"t": ["Concat(Sub(C0,C4))", "Concat(Sub(M(WORD,1,start),M(WORD,1,end)))"]}
    score = raw_scores([task], samples, [1, 2])
    assert score["tasks"][0]["correct"] == 1
    assert score["pass_at_k"] == {"1": 0.5, "2": 1.0}
