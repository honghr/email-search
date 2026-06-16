"""Cohere rerank via Azure AI Foundry.

Calls the deployed Cohere rerank model over its dedicated Foundry endpoint
(".../providers/cohere/v2/rerank"). This moves reranking off the local CPU,
so a 50-document rerank takes ~1s instead of tens of seconds.
"""
from __future__ import annotations

import requests

from app.config import settings


class CohereReranker:
    def __init__(self):
        if not settings.cohere_rerank_url or not settings.azure_openai_api_key:
            raise RuntimeError(
                "Cohere rerank is not configured. Set COHERE_RERANK_URL and "
                "AZURE_OPENAI_API_KEY in backend/.env."
            )
        self.url = settings.cohere_rerank_url
        self.headers = {
            "Authorization": f"Bearer {settings.azure_openai_api_key}",
            "Content-Type": "application/json",
        }
        self.model = settings.cohere_rerank_deployment

    def score(self, query: str, documents: list[str]) -> list[float]:
        """Return a relevance score per document, in the input order."""
        if not documents:
            return []
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": len(documents),
        }
        resp = requests.post(self.url, headers=self.headers,
                             json=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Cohere rerank error {resp.status_code}: {resp.text}")
        results = resp.json().get("results", [])
        scores = [0.0] * len(documents)
        for item in results:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(scores):
                scores[idx] = float(item.get("relevance_score", 0.0))
        return scores
