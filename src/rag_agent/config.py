"""Application settings, loaded from environment / .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Populate os.environ from .env so libraries that read the environment directly
# (langsmith tracing, langchain-tavily) pick up the keys too — pydantic-settings
# alone only fills the Settings object, not os.environ.
load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- credentials ---
    openai_api_key: str
    tavily_api_key: str | None = None

    # --- LangSmith (tracing auto-enables when LANGSMITH_TRACING=true + key set) ---
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "resume-demo-rag-agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # --- models (gpt-5 series only; never gpt-4*) ---
    model_fast: str = "gpt-5.4-mini"
    model_heavy: str = "gpt-5.5"
    embedding_model: str = "text-embedding-3-small"
    reasoning_effort: str = "medium"

    # --- storage / retrieval ---
    chroma_dir: str = "./chroma_db"
    chroma_collection: str = "documents"
    sqlite_path: str = "./memory.sqlite"
    retriever_k: int = 4
    sample_docs_dir: str = "./data/sample_docs"

    @property
    def web_backend(self) -> str:
        return "tavily" if self.tavily_api_key else "duckduckgo"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
