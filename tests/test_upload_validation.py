from fastapi.testclient import TestClient

from rag_agent.api import app


def authenticated_client() -> TestClient:
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"password": "test-password"}).is_success
    return client


def test_disallowed_extension_is_rejected():
    response = authenticated_client().post(
        "/api/ingest", files={"files": ("script.exe", b"hello", "application/octet-stream")}
    )
    assert response.status_code == 415


def test_oversized_file_is_rejected():
    response = authenticated_client().post(
        "/api/ingest", files={"files": ("note.txt", b"01234567890", "text/plain")}
    )
    assert response.status_code == 413


def test_empty_file_is_rejected():
    response = authenticated_client().post(
        "/api/ingest", files={"files": ("note.txt", b"", "text/plain")}
    )
    assert response.status_code == 400


def test_unsafe_filename_is_not_used_as_path(monkeypatch):
    captured: list[str] = []

    def fake_ingest(paths: list[str]) -> int:
        captured.extend(paths)
        return 1

    monkeypatch.setattr("rag_agent.api.ingest_paths", fake_ingest)
    response = authenticated_client().post(
        "/api/ingest",
        files={"files": ("../../outside.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200
    assert captured
    assert all("outside.txt" not in path for path in captured)
    assert response.json()["files"] == ["outside.txt"]
