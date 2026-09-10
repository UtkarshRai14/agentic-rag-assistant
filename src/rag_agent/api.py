"""FastAPI application exposing the LangGraph agent over HTTP + SSE."""

from __future__ import annotations

import os
import tempfile
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from rag_agent.agent import build_agent
from rag_agent.config import settings
from rag_agent.ingest import ensure_seeded, ingest_paths
from rag_agent.schemas import (
    ChatRequest,
    FeedbackRequest,
    HealthResponse,
    IngestResponse,
)
from rag_agent.streaming import agent_event_stream
from rag_agent.vectorstore import collection_count


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-seed the vector store with the sample docs on first boot.
    ensure_seeded()

    # Open the async checkpointer for the whole app lifetime.
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    async with AsyncSqliteSaver.from_conn_string(settings.sqlite_path) as saver:
        app.state.agent = build_agent(checkpointer=saver)
        yield


app = FastAPI(title="Agentic RAG Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo: tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_fast=settings.model_fast,
        model_heavy=settings.model_heavy,
        embedding_model=settings.embedding_model,
        web_backend=settings.web_backend,
        langsmith_tracing=settings.langsmith_tracing,
        documents_indexed=collection_count(),
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(files: list[UploadFile] = File(...)) -> IngestResponse:
    tmp_paths: list[str] = []
    names: list[str] = []
    for f in files:
        suffix = os.path.splitext(f.filename or "upload")[1] or ".txt"
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as out:
            out.write(await f.read())
        # preserve original filename as the source label
        labeled = os.path.join(os.path.dirname(path), f.filename or os.path.basename(path))
        os.replace(path, labeled)
        tmp_paths.append(labeled)
        names.append(f.filename or os.path.basename(labeled))

    try:
        added = ingest_paths(tmp_paths)
    finally:
        for p in tmp_paths:
            try:
                os.remove(p)
            except OSError:
                pass

    return IngestResponse(chunks_added=added, files=names)


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request) -> EventSourceResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    agent = request.app.state.agent

    generator = agent_event_stream(
        agent,
        message=req.message,
        thread_id=thread_id,
        is_disconnected=request.is_disconnected,
    )
    return EventSourceResponse(
        generator,
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest) -> dict:
    """Forward end-user thumbs up/down into LangSmith."""
    try:
        from langsmith import Client

        Client().create_feedback(
            run_id=req.run_id, key=req.key, score=req.score, comment=req.comment
        )
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
