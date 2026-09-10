"""OpenAI embeddings factory."""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from rag_agent.config import settings


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.embedding_model)
