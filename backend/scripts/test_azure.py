"""Smoke-test the Azure OpenAI configuration.

Verifies three things against your .env settings:
  1. The embedding deployment returns a vector of the expected dimension.
  2. The chat deployment answers a trivial prompt.
  3. Query understanding returns structured JSON.

Usage:
    python -m scripts.test_azure
"""
from __future__ import annotations

from app.azure_client import get_client
from app.config import settings


def test_embedding() -> None:
    client = get_client()
    resp = client.embeddings.create(
        model=settings.azure_embed_deployment,
        input=["hello world", "上个月的预算邮件"],
    )
    dim = len(resp.data[0].embedding)
    print(f"[embedding] deployment={settings.azure_embed_deployment} "
          f"vectors={len(resp.data)} dim={dim}")
    assert dim == settings.azure_embed_dim, (
        f"Expected dim {settings.azure_embed_dim}, got {dim}. "
        "Update AZURE_EMBED_DIM in .env to match."
    )


def test_chat() -> None:
    client = get_client()
    resp = client.chat.completions.create(
        model=settings.azure_chat_deployment,
        messages=[{"role": "user", "content": "Reply with the single word: ok"}],
    )
    print(f"[chat] deployment={settings.azure_chat_deployment} "
          f"reply={resp.choices[0].message.content!r}")


def test_query_understanding() -> None:
    from query.understanding import parse_query_azure

    parsed = parse_query_azure("emails sent by me last month about the budget")
    print(f"[understanding] semantic={parsed.semantic_text!r} "
          f"date_from={parsed.filters.date_from} "
          f"date_to={parsed.filters.date_to} "
          f"sender_contains={parsed.filters.sender_contains}")


def main() -> None:
    print(f"endpoint={settings.azure_openai_endpoint}")
    test_embedding()
    test_chat()
    test_query_understanding()
    print("\nAll Azure checks passed.")


if __name__ == "__main__":
    main()
