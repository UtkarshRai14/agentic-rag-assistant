"""Chroma vector store, persisted to disk, with one private collection per user.

Every user's chunks live in their own collection, named after the user's id. A
search, listing or delete only ever opens the collection of the user it runs for,
so one user's documents can never show up in another user's results.
"""

from __future__ import annotations

import re
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma

from rag_agent.config import settings
from rag_agent.embeddings import get_embeddings

# User ids are uuid4 hex strings. The evaluation scripts use a fixed id of their own.
_OWNER_ID = re.compile(r"[a-z0-9]{1,64}")


def _client_settings() -> ChromaSettings:
    return ChromaSettings(
        chroma_api_impl="chromadb.api.segment.SegmentAPI",
        anonymized_telemetry=False,
        is_persistent=True,
    )


@lru_cache
def get_client() -> chromadb.ClientAPI:
    """One shared Chroma client for all collections."""
    return chromadb.PersistentClient(path=settings.chroma_dir, settings=_client_settings())


def collection_name(owner_id: str) -> str:
    """Name of the private collection that holds ``owner_id``'s documents."""
    if not isinstance(owner_id, str) or not _OWNER_ID.fullmatch(owner_id):
        raise ValueError("Invalid document owner id.")
    return f"{settings.chroma_collection}-user-{owner_id}"


@lru_cache(maxsize=1024)
def get_vectorstore(owner_id: str) -> Chroma:
    """The vector store over ``owner_id``'s documents only (created empty if new)."""
    return Chroma(
        collection_name=collection_name(owner_id),
        embedding_function=get_embeddings(),
        client=get_client(),
    )


def list_documents(owner_id: str) -> list[dict]:
    """One entry per uploaded file in the owner's collection, newest first."""
    result = get_vectorstore(owner_id)._collection.get(include=["metadatas"])
    documents: dict[str, dict] = {}
    for metadata in result.get("metadatas") or []:
        metadata = metadata or {}
        content_hash = metadata.get("content_hash")
        if not isinstance(content_hash, str):
            continue
        uploaded_at = metadata.get("uploaded_at")
        entry = documents.setdefault(
            content_hash,
            {
                "id": content_hash,
                "name": str(metadata.get("source") or "document"),
                "chunks": 0,
                "uploaded_at": uploaded_at if isinstance(uploaded_at, int) else None,
            },
        )
        entry["chunks"] += 1
    return sorted(documents.values(), key=lambda d: d["uploaded_at"] or 0, reverse=True)


def delete_document(owner_id: str, document_id: str) -> int:
    """Delete every chunk of one file from the owner's collection. Returns chunks deleted."""
    collection = get_vectorstore(owner_id)._collection
    ids = collection.get(where={"content_hash": document_id}, include=[])["ids"]
    if ids:
        collection.delete(ids=ids)
    return len(ids)
