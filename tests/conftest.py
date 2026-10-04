import pytest
from chromadb.api.shared_system_client import SharedSystemClient
from chromadb.config import Settings as ChromaSettings
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding

from rag_agent import vectorstore
from rag_agent.api import app
from rag_agent.config import settings

TEST_PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def test_settings(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Every test gets its own empty users database and Chroma directory."""
    monkeypatch.setattr(settings, "users_db_path", str(tmp_path / "users.sqlite"))
    monkeypatch.setattr(settings, "chroma_dir", str(tmp_path / "chroma"))
    monkeypatch.setattr(settings, "allow_registration", True)
    monkeypatch.setattr(settings, "frontend_origin", "http://testserver")
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    monkeypatch.setattr(settings, "max_upload_count", 2)
    vectorstore.get_client.cache_clear()
    vectorstore.get_vectorstore.cache_clear()
    yield
    vectorstore.get_client.cache_clear()
    vectorstore.get_vectorstore.cache_clear()


@pytest.fixture
def real_store(monkeypatch: pytest.MonkeyPatch):
    """A real Chroma store in the test's temp dir, with offline fake embeddings.

    Uses Chroma's default backend instead of the deployment's SegmentAPI, whose
    hnswlib dependency is not installable everywhere. The collection logic under
    test is the same.
    """
    monkeypatch.setattr(
        vectorstore, "_client_settings", lambda: ChromaSettings(anonymized_telemetry=False)
    )
    monkeypatch.setattr(vectorstore, "get_embeddings", lambda: DeterministicFakeEmbedding(size=32))
    yield
    vectorstore.get_vectorstore.cache_clear()
    vectorstore.get_client.cache_clear()
    SharedSystemClient.clear_system_cache()


@pytest.fixture
def make_client():
    """Return a factory for TestClients that are logged in as a newly registered user."""

    def make(username: str = "alice", password: str = TEST_PASSWORD, **kwargs) -> TestClient:
        client = TestClient(app, **kwargs)
        response = client.post(
            "/api/auth/register", json={"username": username, "password": password}
        )
        assert response.status_code == 201, response.text
        return client

    return make
