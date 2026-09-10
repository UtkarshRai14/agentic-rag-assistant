"""Agent tools: document retrieval (RAG) and web search.

Both emit a ``sources`` payload on LangGraph's custom stream channel so the
frontend can render citation cards in real time.
"""

from __future__ import annotations

import uuid

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from rag_agent.config import settings
from rag_agent.vectorstore import get_vectorstore


def _emit_sources(tool_name: str, sources: list[dict]) -> None:
    """Best-effort push to the custom stream channel (no-op outside a run)."""
    try:
        writer = get_stream_writer()
    except Exception:
        return
    if writer is not None:
        writer({"kind": "sources", "tool": tool_name, "sources": sources})


@tool("retrieve_documents")
def retrieve_documents(query: str) -> str:
    """Search the user's private document collection for relevant passages.

    Use this for anything that might be answered by the ingested documents.
    """
    retriever = get_vectorstore().as_retriever(search_kwargs={"k": settings.retriever_k})
    docs = retriever.invoke(query)
    if not docs:
        return "No relevant passages found in the document collection."

    sources = [
        {
            "id": str(uuid.uuid4()),
            "kind": "document",
            "title": d.metadata.get("source", "document"),
            "snippet": d.page_content[:300],
            "score": d.metadata.get("score"),
        }
        for d in docs
    ]
    _emit_sources("retrieve_documents", sources)

    return "\n\n".join(
        f"[{i + 1}] (source: {d.metadata.get('source', 'document')})\n{d.page_content}"
        for i, d in enumerate(docs)
    )


def _build_web_search_tool():
    """Tavily when a key is present, otherwise keyless DuckDuckGo."""
    if settings.tavily_api_key:
        from langchain_tavily import TavilySearch

        _tavily = TavilySearch(max_results=5)

        @tool("web_search")
        def web_search(query: str) -> str:
            """Search the public web for current or external information."""
            result = _tavily.invoke({"query": query})
            results = result.get("results", []) if isinstance(result, dict) else []
            sources = [
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
            _emit_sources("web_search", sources)
            if not sources:
                return "No web results found."
            return "\n\n".join(
                f"[{i + 1}] {s['title']} ({s.get('url')})\n{s['snippet']}"
                for i, s in enumerate(sources)
            )

        return web_search

    # Keyless fallback
    from langchain_community.tools import DuckDuckGoSearchResults

    _ddg = DuckDuckGoSearchResults(output_format="list")

    @tool("web_search")
    def web_search(query: str) -> str:
        """Search the public web for current or external information."""
        try:
            results = _ddg.invoke(query)
        except Exception as exc:  # rate limits etc. — degrade gracefully
            return f"Web search temporarily unavailable: {exc}"
        results = results if isinstance(results, list) else []
        sources = [
            {
                "id": str(uuid.uuid4()),
                "kind": "web",
                "title": r.get("title", r.get("link", "result")),
                "url": r.get("link"),
                "snippet": (r.get("snippet") or "")[:300],
            }
            for r in results
        ]
        _emit_sources("web_search", sources)
        if not sources:
            return "No web results found."
        return "\n\n".join(
            f"[{i + 1}] {s['title']} ({s.get('url')})\n{s['snippet']}"
            for i, s in enumerate(sources)
        )

    return web_search


def build_tools() -> list:
    return [retrieve_documents, _build_web_search_tool()]
