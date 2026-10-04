import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from rag_agent import users
from rag_agent.api import app
from rag_agent.auth import AUTH_COOKIE
from rag_agent.config import settings

PASSWORD = "correct-horse-battery"  # the password the make_client fixture registers with
NOTE = {"files": ("note.txt", b"hello", "text/plain")}


def user_id(username: str) -> str:
    return users.authenticate(username, PASSWORD).id


# --- health / auth ----------------------------------------------------------------


def test_health_is_public_and_has_no_document_counts():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["allow_registration"] is True
    assert "documents_indexed" not in body


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/auth/session"),
        ("get", "/api/documents"),
        ("delete", "/api/documents/" + "0" * 64),
        ("post", "/api/chat/stream"),
        ("post", "/api/feedback"),
    ],
)
def test_protected_routes_require_login(method, path):
    response = getattr(TestClient(app), method)(path)
    assert response.status_code == 401


def test_protected_ingest_requires_auth():
    response = TestClient(app).post("/api/ingest", files=NOTE)
    assert response.status_code == 401


def test_register_logs_the_user_in(make_client):
    client = make_client("Alice")
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "user": {"username": "alice"}}


def test_register_rejects_a_taken_username(make_client):
    make_client("alice")
    response = TestClient(app).post(
        "/api/auth/register", json={"username": "ALICE", "password": PASSWORD}
    )
    assert response.status_code == 409


def test_register_rejects_a_weak_password():
    response = TestClient(app).post(
        "/api/auth/register", json={"username": "alice", "password": "short"}
    )
    assert response.status_code == 400
    assert "at least 8" in response.json()["detail"]


def test_registration_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "allow_registration", False)
    client = TestClient(app)
    response = client.post("/api/auth/register", json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 403
    assert client.get("/api/health").json()["allow_registration"] is False


def test_login(make_client):
    make_client("alice")
    client = TestClient(app)
    bad = [("alice", "wrong-password"), ("nobody", PASSWORD)]
    for username, password in bad:
        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == 401
    assert client.get("/api/auth/session").status_code == 401

    response = client.post("/api/auth/login", json={"username": "Alice", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["user"] == {"username": "alice"}
    assert client.get("/api/auth/session").status_code == 200


def test_login_ignores_non_json_bodies(make_client):
    # A cross-site form can POST text/plain without a CORS preflight; that must not log in.
    make_client("alice")
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        content=json.dumps({"username": "alice", "password": PASSWORD}),
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 422
    assert AUTH_COOKIE not in client.cookies


def test_logout_revokes_the_session(make_client):
    client = make_client("alice")
    token = client.cookies.get(AUTH_COOKIE)
    assert token

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/session").status_code == 401
    # A kept copy of the old cookie stops working too.
    assert TestClient(app, cookies={AUTH_COOKIE: token}).get("/api/auth/session").status_code == 401


def test_old_signed_cookies_are_not_accepted():
    client = TestClient(app, cookies={AUTH_COOKIE: "1700000000.deadbeef"})
    assert client.get("/api/auth/session").status_code == 401


# --- ingest -----------------------------------------------------------------------


def test_login_and_authenticated_ingest(make_client, monkeypatch):
    monkeypatch.setattr("rag_agent.api.ingest_paths", lambda owner, paths, names: 1)
    response = make_client().post("/api/ingest", files=NOTE)
    assert response.status_code == 200
    assert response.json()["chunks_added"] == 1


def test_ingest_goes_to_the_uploading_users_collection(make_client, monkeypatch):
    owners: list[str] = []

    def fake_ingest(owner: str, paths: list[str], names: list[str]) -> int:
        owners.append(owner)
        return 1

    monkeypatch.setattr("rag_agent.api.ingest_paths", fake_ingest)
    alice, bob = make_client("alice"), make_client("bob")
    assert alice.post("/api/ingest", files=NOTE).status_code == 200
    assert bob.post("/api/ingest", files=NOTE).status_code == 200
    assert owners == [user_id("alice"), user_id("bob")]
    assert owners[0] != owners[1]


def test_ingestion_runs_off_the_event_loop(make_client, monkeypatch):
    on_event_loop: list[bool] = []

    def fake_ingest(owner: str, paths: list[str], names: list[str]) -> int:
        try:
            asyncio.get_running_loop()
            on_event_loop.append(True)
        except RuntimeError:  # no running loop here, so we are in a worker thread
            on_event_loop.append(False)
        return 1

    monkeypatch.setattr("rag_agent.api.ingest_paths", fake_ingest)
    response = make_client().post("/api/ingest", files=NOTE)
    assert response.status_code == 200
    assert on_event_loop == [False]


def test_document_ids_are_validated(make_client):
    response = make_client().delete("/api/documents/not-a-hash")
    assert response.status_code == 422


# --- chat -------------------------------------------------------------------------


class RecordingAgent:
    def __init__(self) -> None:
        self.configs: list[dict] = []

    async def astream(self, *args, config, **kwargs):
        self.configs.append(config)
        return
        yield


@pytest.fixture
def recording_agent():
    agent = RecordingAgent()
    app.state.agent = agent
    yield agent
    del app.state.agent


def test_chat_runs_as_the_logged_in_user(make_client, recording_agent):
    alice, bob = make_client("alice"), make_client("bob")
    for client in (alice, bob):
        response = client.post(
            "/api/chat/stream", json={"message": "hi", "thread_id": "shared-thread"}
        )
        assert response.status_code == 200
        assert '"thread_id": "shared-thread"' in response.text
        # The internal, user-scoped thread key is never sent to the client.
        assert ":shared-thread" not in response.text

    first, second = (config["configurable"] for config in recording_agent.configs)
    assert first["user_id"] == user_id("alice")
    assert second["user_id"] == user_id("bob")
    # The same thread id from two users is two separate conversations.
    assert first["thread_id"] == f"{user_id('alice')}:shared-thread"
    assert second["thread_id"] == f"{user_id('bob')}:shared-thread"


@pytest.mark.parametrize("thread_id", ["someone:thread", "a/b", "x" * 101, ""])
def test_chat_rejects_malformed_thread_ids(make_client, recording_agent, thread_id):
    response = make_client().post("/api/chat/stream", json={"message": "hi", "thread_id": thread_id})
    assert response.status_code == 422
    assert recording_agent.configs == []
