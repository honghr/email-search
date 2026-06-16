"""FastAPI application exposing the email search engine."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import SearchResponse
from index.qdrant_store import QdrantStore
from search.engine import SearchEngine

state: dict[str, object] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = QdrantStore()
    if not store.exists():
        raise RuntimeError(
            f"Qdrant collection '{settings.qdrant_collection}' not found. "
            "Build it first: python -m index.builder --data <jsonl>"
        )
    state["store"] = store
    state["engine"] = SearchEngine(store)
    yield
    state.clear()


app = FastAPI(title="Email Search API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    store: QdrantStore = state.get("store")  # type: ignore[assignment]
    reranker = (settings.cohere_rerank_deployment
                if settings.cohere_rerank_url else settings.rerank_model)
    return {
        "status": "ok" if store else "no_index",
        "emails": store.count() if store else 0,
        "embed_model": settings.azure_embed_deployment,
        "rerank_model": reranker,
        "chat_model": settings.azure_chat_deployment,
    }


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Natural-language query"),
    top_k: int = Query(default=None, ge=1, le=50),
) -> SearchResponse:
    engine: SearchEngine = state.get("engine")  # type: ignore[assignment]
    if engine is None:
        raise HTTPException(status_code=503, detail="Index not loaded")
    return engine.search(q, top_k=top_k)


@app.post("/api/open")
def open_in_outlook(id: str = Query(..., description="Email EntryID")) -> dict:
    """Open the email in the local Outlook desktop client."""
    try:
        from ingest.open_outlook import open_email

        open_email(id)
        return {"status": "opened"}
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        raise HTTPException(status_code=500, detail=f"Could not open: {exc}")
