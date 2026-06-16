"""Qdrant-backed hybrid email index.

Stores one point per email with two vectors: a dense vector (Azure embedding,
semantic recall) and a BM25 sparse vector (exact keyword recall). Hybrid search
runs both recalls and fuses them server-side with Reciprocal Rank Fusion (RRF),
all inside Qdrant. The sparse vector uses Qdrant's IDF modifier, so BM25 scoring
is owned by the database. Full email bodies are NOT stored here — the UI opens
the original in the local Outlook client.

Metadata filtering (date range, sender name) is pushed down into both recalls so
the candidate set is narrowed server-side before scoring.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import settings
from app.schemas import Email, QueryFilters

_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")

# Named vectors stored per point.
_DENSE = "dense"
_SPARSE = "bm25"


def _point_id(email_id: str) -> str:
    # Deterministic UUID so re-importing the same email overwrites its point.
    return str(uuid.uuid5(_NAMESPACE, email_id))


def _to_ts(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _payload(email: Email) -> dict:
    return {
        "email_id": email.id,
        "subject": email.subject,
        "sender": email.sender,
        "sender_name": email.sender_name,
        "recipients": email.recipients,
        "date": email.date.isoformat() if email.date else None,
        "date_ts": _to_ts(email.date),
        "folder": email.folder,
        "attachments": email.attachments,
        "internet_message_id": email.internet_message_id,
        "snippet": email.snippet(),
    }


class QdrantStore:
    def __init__(self, url: str | None = None, collection: str | None = None):
        self.collection = collection or settings.qdrant_collection
        self.client = QdrantClient(url=url or settings.qdrant_url)

    # --- index-time --------------------------------------------------
    def recreate(self, dim: int) -> None:
        self.client.recreate_collection(
            collection_name=self.collection,
            vectors_config={
                _DENSE: qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
            },
            sparse_vectors_config={
                # IDF modifier: Qdrant computes the BM25 IDF term at query time.
                _SPARSE: qm.SparseVectorParams(modifier=qm.Modifier.IDF),
            },
        )
        self._ensure_payload_indexes()

    def _ensure_payload_indexes(self) -> None:
        """Create the payload indexes used for filter pushdown (idempotent)."""
        self.client.create_payload_index(
            self.collection, "date_ts", qm.PayloadSchemaType.INTEGER)
        # Full-text index lets "Swikriti" match "Swikriti Jain".
        self.client.create_payload_index(
            self.collection, "sender_name", qm.PayloadSchemaType.TEXT)

    def upsert(self, emails: list[Email], dense_vectors,
               sparse_vectors: list[qm.SparseVector]) -> None:
        points = [
            qm.PointStruct(
                id=_point_id(email.id),
                vector={_DENSE: dense.tolist(), _SPARSE: sparse},
                payload=_payload(email),
            )
            for email, dense, sparse in zip(emails, dense_vectors, sparse_vectors)
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def count(self) -> int:
        return self.client.count(self.collection, exact=True).count

    def exists(self) -> bool:
        return self.client.collection_exists(self.collection)

    # --- search-time -------------------------------------------------
    def _build_filter(self, f: QueryFilters):
        must: list = []
        if f.sender_contains:
            must.append(qm.FieldCondition(
                key="sender_name", match=qm.MatchText(text=f.sender_contains)))
        if f.date_from or f.date_to:
            rng = qm.Range(
                gte=_to_ts(f.date_from) if f.date_from else None,
                lte=_to_ts(f.date_to) if f.date_to else None,
            )
            must.append(qm.FieldCondition(key="date_ts", range=rng))
        return qm.Filter(must=must) if must else None

    def search(self, dense_vector, sparse_vector: qm.SparseVector,
               filters: QueryFilters, limit: int):
        """Hybrid recall: dense + BM25 prefetch fused with RRF, server-side."""
        flt = self._build_filter(filters)
        result = self.client.query_points(
            collection_name=self.collection,
            prefetch=[
                qm.Prefetch(query=dense_vector.tolist(), using=_DENSE,
                            filter=flt, limit=limit),
                qm.Prefetch(query=sparse_vector, using=_SPARSE,
                            filter=flt, limit=limit),
            ],
            query=qm.FusionQuery(fusion=qm.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
        return result.points
