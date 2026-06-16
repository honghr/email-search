"""Shared data models for emails, queries and search results."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Email(BaseModel):
    """A normalized email record used for indexing and display."""

    id: str
    subject: str = ""
    body: str = ""
    sender: str = ""
    sender_name: str = ""
    recipients: list[str] = Field(default_factory=list)
    date: Optional[datetime] = None
    attachments: list[str] = Field(default_factory=list)
    folder: str = ""
    # Stable RFC 822 Message-ID (populated by the importer). Used to
    # de-duplicate and to locate the original email when opening it.
    internet_message_id: str = ""

    def index_text(self) -> str:
        """Full text used for embedding. Subject weighted by repetition.

        Not truncated: the complete body is embedded so no content is lost.
        """
        parts = [self.subject, self.subject, self.sender_name, self.body]
        return "\n".join(p for p in parts if p)

    def snippet(self, max_chars: int = 2000) -> str:
        """Shorter text stored for reranking and result display."""
        body = " ".join(self.body.split())
        return body[:max_chars]


class QueryFilters(BaseModel):
    """Structured constraints extracted from a natural-language query."""

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    # Substring matched against the sender's name / address. "from me" maps to
    # the user's own name, so a single field covers all sender filtering.
    sender_contains: Optional[str] = None


class ParsedQuery(BaseModel):
    """Result of query understanding: semantic text + structured filters."""

    original: str
    semantic_text: str
    filters: QueryFilters = Field(default_factory=QueryFilters)
    source: str = "azure"  # "azure" or "degraded"


class SearchHit(BaseModel):
    email: Email
    score: float  # Qdrant RRF fusion score from hybrid recall
    fusion_rank: Optional[int] = None
    rerank_score: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    parsed: ParsedQuery
    hits: list[SearchHit]
    total_candidates: int
