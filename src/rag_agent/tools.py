"""Agent tools: document retrieval (RAG) and web search.

Document retrieval only searches the collection of the user in the run config
(``configurable.user_id``). Both tools emit a ``sources`` payload on LangGraph's
custom stream channel so the frontend can render citation cards in real time. Every source carries a citation
``number`` that is unique within a chat turn: the model reads it in the tool
result and the UI shows the same number on the source card.
"""

from __future__ import annotations

import logging
import threading
import uuid

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from rag_agent.config import settings
from rag_agent.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


class SourceCounter:
    """Hands out citation numbers for one chat turn.

    A new counter is created per turn and travels in the run config, so every tool
    call in the turn shares it and concurrent requests never do. The lock is needed
    because the agent can run several tools at once in different threads.
    """

    def __init__(self) -> None:
        self._last = 0
        self._lock = threading.Lock()

    def take(self, count: int) -> range:
        with self._lock:
            first = self._last + 1
            self._last += count
        return range(first, first + count)


def _number_sources(config: RunnableConfig, sources: list[dict]) -> None:
    """Give each source the next citation number of the current turn."""
    counter = config.get("configurable", {}).get("source_counter") or SourceCounter()
    for number, source in zip(counter.take(len(sources)), sources, strict=True):
        source["number"] = number


def _emit_sources(tool_name: str, sources: list[dict]) -> None:
    """Best-effort push to the custom stream channel (no-op outside a run)."""
    try:
        writer = get_stream_writer()
    except Exception:
        return
    if writer is not None:
        writer({"kind": "sources", "tool": tool_name, "sources": sources})


@tool("retrieve_documents")
def retrieve_documents(query: str, config: RunnableConfig) -> str:
    """Search the user's private document collection for relevant passages.

    Use this for anything that might be answered by the documents the user uploaded.
    """
    # The API puts the logged-in user's id in the run config. Without it there is no
    # collection this request may read, so refuse rather than search anything else.
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        logger.warning("retrieve_documents was called without a user_id; not searching.")
        return "No document collection is available for this request."

    store = get_vectorstore(user_id)
    if store._collection.count() == 0:
        return "The user has not uploaded any documents yet."
    docs = store.as_retriever(search_kwargs={"k": settings.retriever_k}).invoke(query)
    if not docs:
        return "No relevant passages found in the document collection."

    sources = [
        {
            "id": str(uuid.uuid4()),
            "kind": "document",
            "title": d.metadata.get("source", "document"),
            "snippet": d.page_content[:300],
        }
        for d in docs
    ]
    _number_sources(config, sources)
    _emit_sources("retrieve_documents", sources)

    return "\n\n".join(
        f"[{s['number']}] (source: {s['title']})\n{d.page_content}"
        for s, d in zip(sources, docs, strict=True)
    )


def _build_web_search_tool():
    """Tavily when a key is present, otherwise keyless DuckDuckGo."""
    if settings.tavily_api_key:
        from langchain_tavily import TavilySearch

        _tavily = TavilySearch(max_results=5)

        def search(query: str) -> list[dict]:
            result = _tavily.invoke({"query": query})
            results = result.get("results", []) if isinstance(result, dict) else []
            return [
                {
                    "id": str(uuid.uuid4()),
                    "kind": "web",
                    "title": r.get("title", r.get("url", "result")),
                    "url": r.get("url"),
                    "snippet": (r.get("content") or "")[:300],
                    "score": r.get("score"),
                }
                for r in results
            ]

    else:
        from langchain_community.tools import DuckDuckGoSearchResults

        _ddg = DuckDuckGoSearchResults(output_format="list")

        def search(query: str) -> list[dict]:
            results = _ddg.invoke(query)
            results = results if isinstance(results, list) else []
            return [
                {
                    "id": str(uuid.uuid4()),
                    "kind": "web",
                    "title": r.get("title", r.get("link", "result")),
                    "url": r.get("link"),
                    "snippet": (r.get("snippet") or "")[:300],
                }
                for r in results
            ]

    @tool("web_search")
    def web_search(query: str, config: RunnableConfig) -> str:
        """Search the public web for current or external information."""
        try:
            sources = search(query)
        except Exception:  # rate limits, network errors, bad API key, ...
            logger.exception("Web search failed for query %r", query)
            return "Web search is temporarily unavailable."
        if not sources:
            return "No web results found."

        _number_sources(config, sources)
        _emit_sources("web_search", sources)
        return "\n\n".join(
            f"[{s['number']}] {s['title']} ({s.get('url')})\n{s['snippet']}" for s in sources
        )

    return web_search


def build_tools() -> list:
    return [retrieve_documents, _build_web_search_tool()]
