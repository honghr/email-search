"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Data
    data_path: str = "../data/emails.jsonl"

    # Local cross-encoder reranker (downloaded on first run).
    rerank_model: str = "BAAI/bge-reranker-v2-m3"

    # Cohere rerank on Azure AI Foundry (cloud reranker; no local model / GPU).
    # Target URI from the deployment's Details page.
    cohere_rerank_url: str = ""
    cohere_rerank_deployment: str = "Cohere-rerank-v4.0-fast"

    # Retrieval tuning
    recall_top_k: int = 50
    final_top_k: int = 10

    # Reranking is on by default now that it runs on Cohere (Azure cloud),
    # which is fast; set to false to use vector-only ranking.
    use_rerank: bool = True
    # Identity for "sent by me" filtering (matched against sender / folder)
    me_address: str = ""
    me_name: str = ""

    # --- Azure OpenAI -----------------------------------------------------
    # Azure AI Foundry v1 endpoint (ends with /openai/v1); no api_version.
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""

    # Embedding deployment (computes vectors for emails and queries).
    azure_embed_deployment: str = ""
    azure_embed_dim: int = 3072  # text-embedding-3-large default

    # Chat deployment used for query understanding.
    azure_chat_deployment: str = ""

    # --- Qdrant vector database -------------------------------------------
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "emails"

    @property
    def data_file(self) -> Path:
        return (BACKEND_DIR / self.data_path).resolve()


settings = Settings()
