"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rag_agent.users import MAX_PASSWORD_LENGTH


class Credentials(BaseModel):
    # Only size limits here; the account rules live in rag_agent.users.
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=MAX_PASSWORD_LENGTH)


class UserOut(BaseModel):
    username: str


class SessionResponse(BaseModel):
    authenticated: bool
    user: UserOut


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    # Letters, digits, "-" and "_" only (the server-generated ids are UUIDs).
    thread_id: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class FeedbackRequest(BaseModel):
    run_id: str
    score: float
    comment: str | None = None
    key: str = "user_score"


class IngestResponse(BaseModel):
    chunks_added: int
    files: list[str]


class DocumentInfo(BaseModel):
    id: str  # SHA-256 of the file content
    name: str
    chunks: int
    uploaded_at: int | None = None  # unix seconds


class DocumentsResponse(BaseModel):
    documents: list[DocumentInfo]
    total_chunks: int


class DeleteDocumentResponse(BaseModel):
    deleted_chunks: int


class HealthResponse(BaseModel):
    status: str
    model_fast: str
    model_heavy: str
    embedding_model: str
    web_backend: str
    langsmith_tracing: bool
    allow_registration: bool
