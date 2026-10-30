import math


def precision_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero")
    return sum(item in relevant_ids for item in ranked_ids[:k]) / k


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero")
    if not relevant_ids:
        return 0.0
    return sum(item in relevant_ids for item in ranked_ids[:k]) / len(relevant_ids)


def mean_reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, item in enumerate(ranked_ids, start=1):
        if item in relevant_ids:
            return 1 / rank
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero")
    dcg = sum(
        1 / math.log2(rank + 1)
        for rank, item in enumerate(ranked_ids[:k], start=1)
        if item in relevant_ids
    )
    ideal_hits = min(len(relevant_ids), k)
    ideal_dcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0
