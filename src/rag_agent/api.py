"""FastAPI application exposing the LangGraph agent over HTTP + SSE.

Every route except health and the auth routes needs a logged-in user, and works
only on that user's documents and conversations.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Path, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from rag_agent.agent import build_agent
from rag_agent.auth import AUTH_COOKIE, clear_session_cookie, current_user, set_session_cookie
from rag_agent.config import settings
from rag_agent.ingest import SUPPORTED_EXTS, UnreadableDocumentError, ingest_paths
from rag_agent.schemas import (
    ChatRequest,
    Credentials,
    DeleteDocumentResponse,
    DocumentsResponse,
    FeedbackRequest,
    HealthResponse,
    IngestResponse,
    SessionResponse,
    UserOut,
)
from rag_agent.streaming import agent_event_stream
from rag_agent.users import (
    User,
    UsernameTaken,
    authenticate,
    create_session,
    create_user,
    delete_session,
    init_db,
)
from rag_agent.vectorstore import delete_document, list_documents

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the users database if this is the first boot.
    init_db()

    # SQLite does not create missing folders, and nothing else creates this one at
    # startup, so make sure the conversation memory file's folder exists.
    os.makedirs(os.path.dirname(os.path.abspath(settings.sqlite_path)), exist_ok=True)

    # Open the async checkpointer for the whole app lifetime.
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    async with AsyncSqliteSaver.from_conn_string(settings.sqlite_path) as saver:
        app.state.agent = build_agent(checkpointer=saver)
        yield


app = FastAPI(title="Agentic RAG Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "DELETE"],
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
        allow_registration=settings.allow_registration,
    )


# --- auth -----------------------------------------------------------------------
# The auth routes are plain functions, so FastAPI runs them in a worker thread:
# password hashing is deliberately slow and must not block the event loop.


def _session_response(user: User, status_code: int = 200) -> JSONResponse:
    """Start a new session for ``user`` and return it as the response cookie."""
    body = SessionResponse(authenticated=True, user=UserOut(username=user.username))
    response = JSONResponse(body.model_dump(), status_code=status_code)
    set_session_cookie(response, create_session(user.id))
    return response


@app.post("/api/auth/register", status_code=201, response_model=SessionResponse)
def register(credentials: Credentials) -> JSONResponse:
    if not settings.allow_registration:
        raise HTTPException(
            status_code=403, detail="Registration is disabled. Ask an administrator for an account."
        )
    try:
        user = create_user(credentials.username, credentials.password)
    except UsernameTaken as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _session_response(user, status_code=201)


@app.post("/api/auth/login", response_model=SessionResponse)
def login(credentials: Credentials) -> JSONResponse:
    user = authenticate(credentials.username, credentials.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return _session_response(user)


@app.post("/api/auth/logout")
def logout(request: Request) -> JSONResponse:
    delete_session(request.cookies.get(AUTH_COOKIE))
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@app.get("/api/auth/session", response_model=SessionResponse)
def session(user: User = Depends(current_user)) -> SessionResponse:
    return SessionResponse(authenticated=True, user=UserOut(username=user.username))


# --- documents ------------------------------------------------------------------


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(
    files: list[UploadFile] = File(...),
    user: User = Depends(current_user),
) -> IngestResponse:
    if not files or len(files) > settings.max_upload_count:
        raise HTTPException(
            status_code=413,
            detail=f"Upload between 1 and {settings.max_upload_count} files.",
        )
    tmp_paths: list[str] = []
    names: list[str] = []
    try:
        for f in files:
            original_name = (f.filename or "upload.txt").replace("\\", "/").split("/")[-1]
            suffix = "." + original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
            if suffix not in SUPPORTED_EXTS:
                raise HTTPException(
                    status_code=415, detail="Only PDF, TXT, and Markdown files are supported."
                )
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
            tmp_paths.append(path)
            with open(fd, "wb", closefd=True) as out:
                out.write(content)
            names.append(original_name)

        # Embedding is blocking network I/O, so run it off the event loop.
        try:
            added = await asyncio.to_thread(ingest_paths, user.id, tmp_paths, names)
        except UnreadableDocumentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
    finally:
        for p in tmp_paths:
            try:
                os.remove(p)
            except OSError:
                pass

    return IngestResponse(chunks_added=added, files=names)


@app.get("/api/documents", response_model=DocumentsResponse)
async def documents(user: User = Depends(current_user)) -> DocumentsResponse:
    docs = await asyncio.to_thread(list_documents, user.id)
    return DocumentsResponse(documents=docs, total_chunks=sum(d["chunks"] for d in docs))


@app.delete("/api/documents/{document_id}", response_model=DeleteDocumentResponse)
async def remove_document(
    document_id: str = Path(..., pattern=r"^[0-9a-f]{64}$"),
    user: User = Depends(current_user),
) -> DeleteDocumentResponse:
    deleted = await asyncio.to_thread(delete_document, user.id, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DeleteDocumentResponse(deleted_chunks=deleted)


# --- chat -------------------------------------------------------------------------


@app.post("/api/chat/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    user: User = Depends(current_user),
) -> EventSourceResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    agent = request.app.state.agent

    generator = agent_event_stream(
        agent,
        message=req.message,
        thread_id=thread_id,
        user_id=user.id,
        is_disconnected=request.is_disconnected,
    )
    return EventSourceResponse(
        generator,
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/feedback", dependencies=[Depends(current_user)])
def feedback(req: FeedbackRequest) -> dict:
    """Forward end-user thumbs up/down into LangSmith.

    A plain function, so FastAPI runs the blocking LangSmith request in a worker thread.
    """
    try:
        from langsmith import Client

        Client().create_feedback(
            run_id=req.run_id, key=req.key, score=req.score, comment=req.comment
        )
        return {"ok": True}
    except Exception:
        logger.exception("Failed to submit feedback for run %s", req.run_id)
        return {"ok": False, "error": "Feedback could not be submitted."}
