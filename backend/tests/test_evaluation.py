import pytest

from app.services.evaluation import (
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_ranking_metrics() -> None:
    ranked = ["unrelated", "match-a", "match-b"]
    relevant = {"match-a", "match-b"}

    assert precision_at_k(ranked, relevant, 3) == pytest.approx(2 / 3)
    assert recall_at_k(ranked, relevant, 2) == pytest.approx(1 / 2)
    assert mean_reciprocal_rank(ranked, relevant) == pytest.approx(1 / 2)
    assert ndcg_at_k(ranked, relevant, 3) == pytest.approx(0.6934264, abs=1e-6)


def test_metrics_handle_empty_relevant_set() -> None:
    assert recall_at_k(["a"], set(), 1) == 0
    assert mean_reciprocal_rank(["a"], set()) == 0
    assert ndcg_at_k(["a"], set(), 1) == 0


def test_metrics_reject_non_positive_k() -> None:
    with pytest.raises(ValueError):
        precision_at_k(["a"], {"a"}, 0)
