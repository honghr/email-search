"""BM25 sparse embeddings via FastEmbed (Qdrant's own implementation).

Produces sparse vectors for documents and queries. Term frequencies come from
FastEmbed's `Qdrant/bm25`; the IDF term is applied by Qdrant at query time
(the collection's sparse vector uses `Modifier.IDF`), so BM25 scoring stays
owned by the database rather than reimplemented here.
"""
from __future__ import annotations

from functools import lru_cache

from qdrant_client.http import models as qm

_MODEL_NAME = "Qdrant/bm25"
# BM25 ignores token positions, so the dense-side character cap is irrelevant;
# we still bound very long bodies to keep tokenization fast.
_MAX_CHARS = 20000


@lru_cache(maxsize=1)
def _model():
    from fastembed import SparseTextEmbedding

    return SparseTextEmbedding(model_name=_MODEL_NAME)


def _to_sparse(embedding) -> qm.SparseVector:
    return qm.SparseVector(
        indices=[int(i) for i in embedding.indices],
        values=[float(v) for v in embedding.values],
    )


class BM25Embedder:
    def encode(self, texts: list[str]) -> list[qm.SparseVector]:
        if not texts:
            return []
        texts = [t[:_MAX_CHARS] for t in texts]
        return [_to_sparse(e) for e in _model().embed(texts)]

    def encode_query(self, text: str) -> qm.SparseVector:
        emb = next(iter(_model().query_embed([text[:_MAX_CHARS]])))
        return _to_sparse(emb)
