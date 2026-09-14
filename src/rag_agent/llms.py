"""Google Gemini chat model factories."""

from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI

from rag_agent.config import settings


def fast_model() -> ChatGoogleGenerativeAI:
    """Small, cheap model for routine steps."""
    return ChatGoogleGenerativeAI(
        model=settings.model_fast,
        google_api_key=settings.google_api_key,
        streaming=True,
    )


def heavy_model() -> ChatGoogleGenerativeAI:
    """Capable model for planning + answer synthesis."""
    return ChatGoogleGenerativeAI(
        model=settings.model_heavy,
        google_api_key=settings.google_api_key,
        streaming=True,
    )
