"""Document ingestion: load -> split -> embed -> persist to the owner's Chroma collection."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_agent.config import settings
from rag_agent.vectorstore import get_vectorstore

_TEXT_EXTS = {".txt", ".md", ".markdown"}
_PDF_EXTS = {".pdf"}
SUPPORTED_EXTS = _TEXT_EXTS | _PDF_EXTS

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


class UnreadableDocumentError(ValueError):
    """A file has no text that can be indexed. The message is safe to show to users."""


def _load_file(path: str) -> list[Document]:
    if Path(path).suffix.lower() in _PDF_EXTS:
        return PyPDFLoader(path).load()
    return TextLoader(path, encoding="utf-8").load()  # .txt / .md / .markdown


def ingest_paths(owner_id: str, paths: list[str], names: list[str]) -> int:
    """Add the given files to ``owner_id``'s private collection. Returns chunks added.

    ``names`` are the display names (one per path) stored as each document's
    ``source``, because the paths may be temporary files with meaningless names.
    A file whose content is already in the owner's collection is skipped. Other
    users' collections are never read, so the same file can be in several of them.
    If any file cannot be read or has no text, ``UnreadableDocumentError`` is raised
    and nothing is added.
    """
    store = get_vectorstore(owner_id)
    uploaded_at = int(time.time())
    chunks: list[Document] = []
    ids: list[str] = []
    seen_hashes: set[str] = set()
    for path, name in zip(paths, names, strict=True):
        content_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        existing = store._collection.get(where={"content_hash": content_hash}, limit=1, include=[])
        if existing.get("ids"):
            continue

        try:
            docs = _load_file(path)
        except Exception as exc:  # e.g. a damaged PDF or a text file that is not UTF-8
            raise UnreadableDocumentError(
                f"Could not read {name}. Upload a valid PDF, or a text or Markdown file "
                "saved as UTF-8."
            ) from exc
        for d in docs:
            d.metadata["source"] = name
            d.metadata["content_hash"] = content_hash
            d.metadata["uploaded_at"] = uploaded_at
        file_chunks = _splitter.split_documents(docs)
        if not file_chunks:  # e.g. a scanned PDF, which has no text layer
            raise UnreadableDocumentError(
                f"{name} has no text to index. Scanned PDFs (images of text) are not supported."
            )
        chunks.extend(file_chunks)
        ids.extend(f"{content_hash}-{index}" for index in range(len(file_chunks)))

    if not chunks:
        return 0

    store.add_documents(chunks, ids=ids)
    return len(chunks)


def ingest_directory(owner_id: str, directory: str | None = None) -> int:
    """Ingest every supported file under ``directory`` into ``owner_id``'s collection."""
    directory = directory or settings.sample_docs_dir
    root = Path(directory)
    if not root.exists():
        return 0
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    return ingest_paths(owner_id, [str(p) for p in files], [p.name for p in files])
