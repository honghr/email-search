"""Shared Azure OpenAI client (Azure AI Foundry v1 API).

The Foundry v1 endpoint (".../openai/v1") uses the standard OpenAI client
with a base_url, so no api_version is required.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def get_client():
    from openai import OpenAI

    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        raise RuntimeError(
            "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT and "
            "AZURE_OPENAI_API_KEY in backend/.env."
        )
    return OpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )
