"""Azure OpenAI embedder (Azure AI Foundry v1 API).

Computes dense vectors for emails (at index time) and queries (at search
time). Both must use the same deployment so they live in one vector space.
"""
from __future__ import annotations

import numpy as np

from app.azure_client import get_client
from app.config import settings

# Azure embeddings accept a limited number of inputs per request.
_BATCH = 64

# text-embedding-3 models accept at most 8192 tokens per input. Without a
# tokenizer we cap by characters at a level safe for any language (even dense
# CJK where a character can be ~1 token). Only the embedding input is
# truncated; the stored snippet and the original email stay intact.
_MAX_CHARS = 8000


class AzureEmbedder:
    def __init__(self, deployment: str | None = None):
        self.deployment = deployment or settings.azure_embed_deployment
        self.client = get_client()

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, settings.azure_embed_dim), dtype=np.float32)
        texts = [t[:_MAX_CHARS] for t in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH):
            batch = texts[start:start + _BATCH]
            resp = self.client.embeddings.create(
                model=self.deployment, input=batch)
            vectors.extend(item.embedding for item in resp.data)
        return np.asarray(vectors, dtype=np.float32)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]
