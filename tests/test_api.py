import asyncio

from fastapi.testclient import TestClient

from rag_agent.api import app


def test_health_shape():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_ingest_requires_auth():
    response = TestClient(app).post(
        "/api/ingest", files={"files": ("note.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 401


def test_login_and_authenticated_ingest(monkeypatch):
    monkeypatch.setattr("rag_agent.api.ingest_paths", lambda paths, names: 1)
    client = TestClient(app)
    login = client.post("/api/auth/login", json={"password": "test-password"})
    assert login.status_code == 200
    response = client.post(
        "/api/ingest", files={"files": ("note.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 200
    assert response.json()["chunks_added"] == 1


def test_invalid_credentials_are_rejected():
    response = TestClient(app).post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401


def test_ingestion_runs_off_the_event_loop(monkeypatch):
    on_event_loop: list[bool] = []

    def fake_ingest(paths: list[str], names: list[str]) -> int:
        try:
            asyncio.get_running_loop()
            on_event_loop.append(True)
        except RuntimeError:  # no running loop here, so we are in a worker thread
            on_event_loop.append(False)
        return 1

    monkeypatch.setattr("rag_agent.api.ingest_paths", fake_ingest)
    client = TestClient(app)
    client.post("/api/auth/login", json={"password": "test-password"})
    response = client.post(
        "/api/ingest", files={"files": ("note.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 200
    assert on_event_loop == [False]
