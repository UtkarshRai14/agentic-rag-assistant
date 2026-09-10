"""The LangGraph agent: an agentic RAG + web-search loop via create_agent."""

from __future__ import annotations

from langchain.agents import create_agent

from rag_agent.llms import heavy_model
from rag_agent.tools import build_tools

SYSTEM_PROMPT = """You are a meticulous research assistant.

Plan before you act, then use your tools to gather evidence:
- `retrieve_documents` — search the user's PRIVATE document collection. Prefer this
  for anything that may be covered by the user's own documents.
- `web_search` — search the PUBLIC web for current events or external facts.

You may call tools multiple times and combine both sources. When the document
collection and the web disagree, say so explicitly.

Always write the final answer with inline numeric citations like [1], [2] that
map, in order, to the specific sources you actually used. If you could not find
relevant evidence, say so honestly rather than guessing."""


def build_agent(checkpointer=None):
    """Return a compiled LangGraph agent.

    The returned graph is automatically traced by LangSmith (via env) and
    streamable through ``astream(stream_mode=[...])``.
    """
    return create_agent(
        model=heavy_model(),
        tools=build_tools(),
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
