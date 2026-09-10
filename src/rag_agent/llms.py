"""ChatOpenAI factories. gpt-5 series only — gpt-4* chat models are forbidden."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from rag_agent.config import settings


def _assert_gpt5(model: str) -> None:
    if model.startswith(("gpt-4", "gpt-3")):
        raise ValueError(
            f"Refusing to use obsolete chat model {model!r}; use the gpt-5 series."
        )


def fast_model() -> ChatOpenAI:
    """Small, cheap model for routine steps."""
    _assert_gpt5(settings.model_fast)
    return ChatOpenAI(model=settings.model_fast, streaming=True)


def heavy_model() -> ChatOpenAI:
    """Capable reasoning model for planning + answer synthesis.

    Passing ``reasoning`` makes langchain-openai route through the Responses API.
    """
    _assert_gpt5(settings.model_heavy)
    return ChatOpenAI(
        model=settings.model_heavy,
        streaming=True,
        reasoning={"effort": settings.reasoning_effort},
    )
