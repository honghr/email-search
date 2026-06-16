"""Query understanding via Azure OpenAI (Azure AI Foundry v1 API).

Splits a natural-language query into semantic text and structured filters
(date range, sender). Only the query string is sent to the model, never email
content. On any Azure error the search degrades gracefully to a plain semantic
query rather than failing.
"""
from __future__ import annotations

import json
from datetime import datetime

from app.azure_client import get_client
from app.config import settings
from app.schemas import ParsedQuery, QueryFilters

_SYSTEM = (
    "You extract search intent from an email search query. "
    "Return strict JSON with keys: semantic_text (string, the topical part "
    "to search, with time/sender phrases removed), date_from (ISO date or "
    "null), date_to (ISO date or null), sender (string or null: the name of "
    "the person the email is from, if the query restricts by sender; use the "
    "literal word 'me' when the user refers to themselves). "
    "Resolve relative dates using the provided current date."
)


def parse_query(query: str) -> ParsedQuery:
    """Parse a query into semantic text + filters, with a safe fallback."""
    try:
        return parse_query_azure(query)
    except Exception:
        return ParsedQuery(original=query, semantic_text=query,
                           filters=QueryFilters(), source="degraded")


def parse_query_azure(query: str) -> ParsedQuery:
    client = get_client()
    today = datetime.now().strftime("%Y-%m-%d")
    response = client.chat.completions.create(
        model=settings.azure_chat_deployment,
        response_format={"type": "json_object"},
        # Deterministic understanding: the same query must always parse to the
        # same filters, so results are reproducible and evaluation is stable.
        temperature=0,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",
             "content": f"Current date: {today}\nQuery: {query}"},
        ],
    )
    data = json.loads(response.choices[0].message.content)

    def _dt(value, end: bool = False):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(str(value))
            if end:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            return None

    sender = (data.get("sender") or "").strip() or None
    if sender and sender.lower() in ("me", "myself", "i"):
        sender = settings.me_name or settings.me_address or None

    filters = QueryFilters(
        date_from=_dt(data.get("date_from")),
        date_to=_dt(data.get("date_to"), end=True),
        sender_contains=sender,
    )
    semantic = (data.get("semantic_text") or query).strip() or query
    return ParsedQuery(original=query, semantic_text=semantic,
                       filters=filters, source="azure")

