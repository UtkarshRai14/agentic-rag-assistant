"""Document ingestion: load -> split -> embed -> persist to Chroma."""

from __future__ import annotations

import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_agent.config import settings
from rag_agent.vectorstore import collection_count, get_vectorstore

_TEXT_EXTS = {".txt", ".md", ".markdown"}
_PDF_EXTS = {".pdf"}

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


def _load_file(path: str) -> list[Document]:
    ext = Path(path).suffix.lower()
    if ext in _PDF_EXTS:
        return PyPDFLoader(path).load()
    if ext in _TEXT_EXTS:
        return TextLoader(path, encoding="utf-8").load()
    # default: treat as plain text
    return TextLoader(path, encoding="utf-8").load()


def ingest_paths(paths: list[str]) -> int:
    """Ingest the given files. Returns the number of chunks added."""
    docs: list[Document] = []
    for p in paths:
        loaded = _load_file(p)
        for d in loaded:
            d.metadata.setdefault("source", os.path.basename(p))
        docs.extend(loaded)

    if not docs:
        return 0

    chunks = _splitter.split_documents(docs)
    get_vectorstore().add_documents(chunks)
    return len(chunks)


def ingest_directory(directory: str | None = None) -> int:
    directory = directory or settings.sample_docs_dir
    root = Path(directory)
    if not root.exists():
        return 0
    paths = [
        str(p)
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in (_TEXT_EXTS | _PDF_EXTS)
    ]
    return ingest_paths(paths)


def ensure_seeded() -> int:
    """Auto-ingest sample docs on first boot when the collection is empty."""
    if collection_count() > 0:
        return 0
    return ingest_directory()
