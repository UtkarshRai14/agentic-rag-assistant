"""Chroma vector store, persisted to disk for zero-setup RAG."""

from __future__ import annotations

from functools import lru_cache

from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma

from rag_agent.config import settings
from rag_agent.embeddings import get_embeddings


@lru_cache
def get_vectorstore() -> Chroma:
    client_settings = ChromaSettings(
        chroma_api_impl="chromadb.api.segment.SegmentAPI",
        anonymized_telemetry=False,
        is_persistent=True,
    )

    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
        client_settings=client_settings,
    )


def collection_count() -> int:
    """Number of stored chunks (0 when empty / fresh)."""
    try:
        return get_vectorstore()._collection.count()
    except Exception:
        return 0