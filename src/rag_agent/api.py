"""FastAPI application exposing the LangGraph agent over HTTP + SSE."""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from rag_agent.agent import build_agent
from rag_agent.auth import AUTH_COOKIE, create_session, require_auth
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

logger = logging.getLogger(__name__)


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
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
    allow_credentials=True,
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


@app.post("/api/auth/login")
async def login(request: Request) -> JSONResponse:
    body = await request.json()
    password = body.get("password") if isinstance(body, dict) else None
    if not settings.app_auth_password or not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication is not configured.")
    if not isinstance(password, str) or password != settings.app_auth_password:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    response = JSONResponse({"ok": True})
    response.set_cookie(
        AUTH_COOKIE,
        create_session(),
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    return response


@app.get("/api/auth/session")
async def session(request: Request) -> dict:
    require_auth(request)
    return {"authenticated": True}


@app.post("/api/ingest", response_model=IngestResponse, dependencies=[Depends(require_auth)])
async def ingest(files: list[UploadFile] = File(...)) -> IngestResponse:
    if not files or len(files) > settings.max_upload_count:
        raise HTTPException(
            status_code=413,
            detail=f"Upload between 1 and {settings.max_upload_count} files.",
        )
    tmp_paths: list[str] = []
    names: list[str] = []
    for f in files:
        original_name = (f.filename or "upload.txt").replace("\\", "/").split("/")[-1]
        suffix = "." + original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if suffix not in {".pdf", ".txt", ".md", ".markdown"}:
            raise HTTPException(status_code=415, detail="Only PDF, TXT, and Markdown files are supported.")
        content = await f.read(settings.max_upload_bytes + 1)
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded files must not be empty.")
        if len(content) > settings.max_upload_bytes:
            limit_mb = settings.max_upload_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"Each uploaded file must be {limit_mb} MB or smaller.",
            )
        fd, path = tempfile.mkstemp(suffix=suffix)
        with open(fd, "wb", closefd=True) as out:
            out.write(content)
        tmp_paths.append(path)
        names.append(original_name)

    try:
        added = ingest_paths(tmp_paths)
    finally:
        for p in tmp_paths:
            try:
                os.remove(p)
            except OSError:
                pass

    return IngestResponse(chunks_added=added, files=names)


@app.post("/api/chat/stream", dependencies=[Depends(require_auth)])
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


@app.post("/api/feedback", dependencies=[Depends(require_auth)])
async def feedback(req: FeedbackRequest) -> dict:
    """Forward end-user thumbs up/down into LangSmith."""
    try:
        from langsmith import Client

        Client().create_feedback(
            run_id=req.run_id, key=req.key, score=req.score, comment=req.comment
        )
        return {"ok": True}
    except Exception:
        logger.exception("Failed to submit feedback for run %s", req.run_id)
        return {"ok": False, "error": "Feedback could not be submitted."}
