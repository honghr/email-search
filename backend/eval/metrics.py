"""Retrieval quality metrics: Recall@K, Precision@R, MRR, nDCG@K.

Relevance can be binary (id in the relevant set) or graded (id -> grade).
"""
from __future__ import annotations

import math


def recall_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    hit = sum(1 for i in ranked_ids[:k] if i in relevant)
    return hit / len(relevant)


def precision_at_r(ranked_ids: list[str], relevant: set[str]) -> float:
    """R-Precision: precision over the top R results, R = #relevant.

    Self-normalizing, so it is not unfairly low when a query has few
    relevant emails. At rank R it equals Recall@R.
    """
    r = len(relevant)
    if r == 0:
        return 0.0
    hit = sum(1 for i in ranked_ids[:r] if i in relevant)
    return hit / r


def reciprocal_rank(ranked_ids: list[str], relevant: set[str]) -> float:
    for rank, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_ids: list[str], grades: dict[str, float], k: int) -> float:
    if not grades:
        return 0.0
    dcg = 0.0
    for i, doc_id in enumerate(ranked_ids[:k]):
        rel = grades.get(doc_id, 0.0)
        if rel:
            dcg += rel / math.log2(i + 2)
    ideal = sorted(grades.values(), reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal))
    return dcg / idcg if idcg else 0.0
