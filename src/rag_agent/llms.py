"""Google Gemini chat model factory."""

from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI

from rag_agent.config import settings


def heavy_model() -> ChatGoogleGenerativeAI:
    """Capable model for planning + answer synthesis."""
    return ChatGoogleGenerativeAI(
        model=settings.model_heavy,
        google_api_key=settings.google_api_key,
        streaming=True,
    )
