"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str | None = None


class FeedbackRequest(BaseModel):
    run_id: str
    score: float
    comment: str | None = None
    key: str = "user_score"


class IngestResponse(BaseModel):
    chunks_added: int
    files: list[str]


class HealthResponse(BaseModel):
    status: str
    model_fast: str
    model_heavy: str
    embedding_model: str
    web_backend: str
    langsmith_tracing: bool
    documents_indexed: int
