"""Translate LangGraph's astream output into a flat SSE event stream.

Stream modes used (astream yields ``(mode, chunk)`` tuples for a list):
- ``messages`` -> assistant token deltas              -> ``token`` events
- ``updates``  -> per-node results (tool calls/results) -> ``tool_start`` / ``tool_end``
- ``custom``   -> our retriever/web payloads            -> ``sources`` events
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage


def _sse(event: str, data: dict) -> dict:
    """Shape expected by sse_starlette.EventSourceResponse."""
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def _result_preview(content: Any, limit: int = 500) -> str:
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    return text[:limit]


async def agent_event_stream(
    agent,
    message: str,
    thread_id: str,
    is_disconnected=None,
) -> AsyncIterator[dict]:
    """Yield SSE event dicts for a single chat turn."""
    config = {"configurable": {"thread_id": thread_id}}
    seen_tool_starts: set[str] = set()

    yield _sse("start", {"thread_id": thread_id})

    try:
        async for mode, chunk in agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            stream_mode=["messages", "updates", "custom"],
        ):
            if is_disconnected is not None and await is_disconnected():
                break

            if mode == "messages":
                msg, meta = chunk
                if isinstance(msg, AIMessageChunk):
                    text = msg.text  # concatenates text blocks, ignores reasoning
                    if text:
                        yield _sse(
                            "token",
                            {
                                "thread_id": thread_id,
                                "delta": text,
                                "node": meta.get("langgraph_node", ""),
                            },
                        )

            elif mode == "updates":
                for node_name, node_update in (chunk or {}).items():
                    messages = (node_update or {}).get("messages", []) or []
                    for m in messages:
                        # model node decided to call tools
                        if isinstance(m, AIMessage) and m.tool_calls:
                            for tc in m.tool_calls:
                                tc_id = tc.get("id") or tc.get("name", "")
                                if tc_id in seen_tool_starts:
                                    continue
                                seen_tool_starts.add(tc_id)
                                yield _sse(
                                    "tool_start",
                                    {
                                        "thread_id": thread_id,
                                        "id": tc_id,
                                        "tool": tc.get("name", ""),
                                        "args": tc.get("args", {}),
                                    },
                                )
                        # tools node returned a result
                        if isinstance(m, ToolMessage):
                            yield _sse(
                                "tool_end",
                                {
                                    "thread_id": thread_id,
                                    "id": m.tool_call_id,
                                    "tool": m.name or "",
                                    "ok": getattr(m, "status", "success") != "error",
                                    "result_preview": _result_preview(m.content),
                                },
                            )

            elif mode == "custom":
                if isinstance(chunk, dict) and chunk.get("kind") == "sources":
                    yield _sse(
                        "sources",
                        {
                            "thread_id": thread_id,
                            "tool": chunk.get("tool", ""),
                            "sources": chunk.get("sources", []),
                        },
                    )

    except Exception as exc:  # surface as a fatal SSE error, don't 500 mid-stream
        yield _sse(
            "error",
            {"thread_id": thread_id, "message": str(exc), "fatal": True},
        )

    yield _sse("end", {"thread_id": thread_id})
