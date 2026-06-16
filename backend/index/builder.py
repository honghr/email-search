"""Build the Qdrant hybrid email index from a JSONL data file.

Computes dense vectors with Azure OpenAI and BM25 sparse vectors with FastEmbed,
then upserts both into Qdrant along with metadata and a display snippet.

Usage:
    python -m index.builder --data ../data/emails.jsonl
    python -m index.builder            # uses DATA_PATH from .env
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.config import settings
from index.azure_embedder import AzureEmbedder
from index.bm25_embedder import BM25Embedder
from index.qdrant_store import QdrantStore
from ingest.normalize import load_emails

_UPSERT_BATCH = 128


def build_index(data_file: Path) -> int:
    emails = load_emails(data_file)
    if not emails:
        raise SystemExit(f"No emails found in {data_file}")
    print(f"Loaded {len(emails)} emails from {data_file}")

    embedder = AzureEmbedder()
    bm25 = BM25Embedder()
    store = QdrantStore()
    store.recreate(settings.azure_embed_dim)
    print(f"Recreated Qdrant collection '{settings.qdrant_collection}' "
          f"(dense dim={settings.azure_embed_dim} + BM25 sparse)")

    start = time.time()
    for i in range(0, len(emails), _UPSERT_BATCH):
        batch = emails[i:i + _UPSERT_BATCH]
        texts = [e.index_text() for e in batch]
        dense_vectors = embedder.encode(texts)
        sparse_vectors = bm25.encode(texts)
        store.upsert(batch, dense_vectors, sparse_vectors)
        print(f"  indexed {min(i + _UPSERT_BATCH, len(emails))}/{len(emails)}")

    total = store.count()
    print(f"Done in {time.time() - start:.1f}s. Collection has {total} points.")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Qdrant email index")
    parser.add_argument("--data", type=str, default=None,
                        help="Path to JSONL email data (defaults to DATA_PATH)")
    args = parser.parse_args()

    data_file = Path(args.data).resolve() if args.data else settings.data_file
    build_index(data_file)


if __name__ == "__main__":
    main()
