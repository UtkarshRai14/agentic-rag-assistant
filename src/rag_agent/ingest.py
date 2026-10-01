"""Document ingestion: load -> split -> embed -> persist to Chroma."""

from __future__ import annotations

import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_agent.config import settings
from rag_agent.vectorstore import collection_count, get_vectorstore

_TEXT_EXTS = {".txt", ".md", ".markdown"}
_PDF_EXTS = {".pdf"}
SUPPORTED_EXTS = _TEXT_EXTS | _PDF_EXTS

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


def _load_file(path: str) -> list[Document]:
    if Path(path).suffix.lower() in _PDF_EXTS:
        return PyPDFLoader(path).load()
    return TextLoader(path, encoding="utf-8").load()  # .txt / .md / .markdown


def ingest_paths(paths: list[str], names: list[str]) -> int:
    """Ingest the given files. Returns the number of chunks added.

    ``names`` are the display names (one per path) stored as each document's
    ``source``, because the paths may be temporary files with meaningless names.
    """
    chunks: list[Document] = []
    ids: list[str] = []
    seen_hashes: set[str] = set()
    for path, name in zip(paths, names, strict=True):
        content_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        existing = get_vectorstore()._collection.get(
            where={"content_hash": content_hash}, limit=1
        )
        if existing.get("ids"):
            continue

        docs = _load_file(path)
        for d in docs:
            d.metadata["source"] = name
            d.metadata["content_hash"] = content_hash
        file_chunks = _splitter.split_documents(docs)
        chunks.extend(file_chunks)
        ids.extend(f"{content_hash}-{index}" for index in range(len(file_chunks)))

    if not chunks:
        return 0

    get_vectorstore().add_documents(chunks, ids=ids)
    return len(chunks)


def ingest_directory(directory: str | None = None) -> int:
    directory = directory or settings.sample_docs_dir
    root = Path(directory)
    if not root.exists():
        return 0
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    return ingest_paths([str(p) for p in files], [p.name for p in files])


def ensure_seeded() -> int:
    """Auto-ingest sample docs on first boot when the collection is empty."""
    if collection_count() > 0:
        return 0
    return ingest_directory()
