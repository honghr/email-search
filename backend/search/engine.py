"""Search engine: hybrid recall (Azure dense + BM25 sparse) -> rerank.

Query understanding (Azure LLM) splits the query into semantic text and
structured filters. The filters are pushed down to Qdrant. The semantic text is
embedded for dense recall, while the original query drives BM25 sparse recall;
Qdrant fuses the two with RRF server-side. A cross-encoder then reranks the
fused candidate pool for final ordering.
"""
from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.schemas import Email, SearchHit, SearchResponse
from index.qdrant_store import QdrantStore
from query.understanding import parse_query


def _email_from_payload(payload: dict) -> Email:
    date = None
    raw = payload.get("date")
    if raw:
        try:
            date = datetime.fromisoformat(raw)
        except ValueError:
            date = None
    return Email(
        id=payload.get("email_id", ""),
        subject=payload.get("subject", ""),
        body=payload.get("snippet", ""),
        sender=payload.get("sender", ""),
        sender_name=payload.get("sender_name", ""),
        recipients=payload.get("recipients", []) or [],
        date=date,
        attachments=payload.get("attachments", []) or [],
        folder=payload.get("folder", ""),
        internet_message_id=payload.get("internet_message_id", ""),
    )


class SearchEngine:
    def __init__(self, store: QdrantStore, reranker=None):
        self.store = store
        self._reranker = reranker

    @property
    def reranker(self):
        if self._reranker is None:
            if settings.cohere_rerank_url:
                from search.cohere_reranker import CohereReranker
                self._reranker = CohereReranker()
            else:
                from search.reranker import Reranker
                self._reranker = Reranker(settings.rerank_model)
        return self._reranker

    def search(self, query: str, *, use_rerank: bool | None = None,
               top_k: int | None = None,
               recall_k: int | None = None) -> SearchResponse:
        top_k = top_k or settings.final_top_k
        recall_k = recall_k or settings.recall_top_k
        if use_rerank is None:
            use_rerank = settings.use_rerank
        parsed = parse_query(query)

        # 1) Hybrid recall from Qdrant: dense (semantic) + BM25 (keywords)
        #    fused server-side with RRF. Metadata filters are pushed down.
        from index.azure_embedder import AzureEmbedder
        from index.bm25_embedder import BM25Embedder
        qvec = AzureEmbedder().encode_one(parsed.semantic_text)
        svec = BM25Embedder().encode_query(query)
        points = self.store.search(qvec, svec, parsed.filters, recall_k)
        if not points:
            return SearchResponse(query=query, parsed=parsed, hits=[],
                                  total_candidates=0)

        emails = [_email_from_payload(p.payload) for p in points]
        fusion_scores = [float(p.score) for p in points]

        # 2) Optional cross-encoder rerank of the recall pool.
        order = list(range(len(emails)))
        rerank_scores: dict[int, float] = {}
        if use_rerank:
            docs = [f"{e.subject}\n{e.body}" for e in emails]
            scores = self.reranker.score(parsed.semantic_text, docs)
            rerank_scores = {i: float(s) for i, s in enumerate(scores)}
            order = sorted(order, key=lambda i: rerank_scores[i], reverse=True)

        # 3) Assemble hits. `score` is the Qdrant RRF fusion score from hybrid
        #    recall; the UI prefers rerank_score when reranking is on.
        hits: list[SearchHit] = []
        for i in order[:top_k]:
            hits.append(SearchHit(
                email=emails[i],
                score=fusion_scores[i],
                fusion_rank=i + 1,
                rerank_score=rerank_scores.get(i),
            ))
        return SearchResponse(query=query, parsed=parsed, hits=hits,
                              total_candidates=len(points))

