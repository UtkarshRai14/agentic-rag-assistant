"""Chroma vector store, persisted to disk for zero-setup RAG."""

from __future__ import annotations

from functools import lru_cache

from langchain_chroma import Chroma

from rag_agent.config import settings
from rag_agent.embeddings import get_embeddings


@lru_cache
def get_vectorstore() -> Chroma:
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
    )


def collection_count() -> int:
    """Number of stored chunks (0 when empty / fresh)."""
    try:
        return get_vectorstore()._collection.count()
    except Exception:
        return 0
