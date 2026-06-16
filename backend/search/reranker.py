"""Cross-encoder reranker backed by bge-reranker-v2-m3 (local, multilingual).

A cross-encoder scores each (query, document) pair jointly, which is far
more accurate than the bi-encoder used for first-stage recall. It is only
applied to the small candidate set returned by vector retrieval.
"""
from __future__ import annotations


class Reranker:
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder

        self.model_name = model_name
        self.model = CrossEncoder(model_name)

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        pairs = [(query, doc) for doc in documents]
        scores = self.model.predict(pairs)
        return [float(s) for s in scores]
