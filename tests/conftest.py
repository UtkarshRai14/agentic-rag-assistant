import pytest

from rag_agent.config import settings


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "app_auth_password", "test-password")
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    monkeypatch.setattr(settings, "frontend_origin", "http://testserver")
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    monkeypatch.setattr(settings, "max_upload_count", 2)
