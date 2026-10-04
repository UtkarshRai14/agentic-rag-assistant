"""Per-user document isolation, tested against a real Chroma store (fake embeddings)."""

import pytest

from rag_agent import users
from rag_agent.config import settings
from rag_agent.ingest import ingest_paths
from rag_agent.tools import SourceCounter, retrieve_documents
from rag_agent.vectorstore import collection_name, delete_document, list_documents

pytestmark = pytest.mark.usefixtures("real_store")

ALICE = "a" * 32
BOB = "b" * 32
PASSWORD = "correct-horse-battery"  # the password the make_client fixture registers with
ALICE_TEXT = "Alice's secret launch code is 1234."
BOB_TEXT = "Bob's favourite colour is green."


def write(tmp_path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def search(user_id: str, query: str = "what do my documents say?") -> str:
    config = {"configurable": {"user_id": user_id, "source_counter": SourceCounter()}}
    return retrieve_documents.invoke({"query": query}, config=config)


def test_users_only_retrieve_their_own_documents(tmp_path):
    ingest_paths(ALICE, [write(tmp_path, "alice.md", ALICE_TEXT)], ["alice.md"])
    ingest_paths(BOB, [write(tmp_path, "bob.md", BOB_TEXT)], ["bob.md"])

    alice_result, bob_result = search(ALICE), search(BOB)

    assert ALICE_TEXT in alice_result and "alice.md" in alice_result
    assert BOB_TEXT not in alice_result and "bob.md" not in alice_result
    assert BOB_TEXT in bob_result and "bob.md" in bob_result
    assert ALICE_TEXT not in bob_result and "alice.md" not in bob_result


def test_a_user_without_documents_gets_nothing(tmp_path):
    ingest_paths(ALICE, [write(tmp_path, "alice.md", ALICE_TEXT)], ["alice.md"])
    assert search(BOB) == "The user has not uploaded any documents yet."


def test_retrieval_without_a_user_searches_nothing(tmp_path):
    ingest_paths(ALICE, [write(tmp_path, "alice.md", ALICE_TEXT)], ["alice.md"])
    result = retrieve_documents.invoke(
        {"query": "launch code"}, config={"configurable": {"source_counter": SourceCounter()}}
    )
    assert result == "No document collection is available for this request."


def test_the_same_file_can_be_in_several_users_collections(tmp_path):
    path = write(tmp_path, "shared.md", "Shared handbook text.")
    assert ingest_paths(ALICE, [path], ["shared.md"]) > 0
    # Not skipped as a duplicate of Alice's copy: users never see each other's files.
    assert ingest_paths(BOB, [path], ["shared.md"]) > 0
    # Uploading it again to the same user is skipped.
    assert ingest_paths(ALICE, [path], ["shared.md"]) == 0
    assert [d["name"] for d in list_documents(ALICE)] == ["shared.md"]
    assert [d["name"] for d in list_documents(BOB)] == ["shared.md"]


def test_users_can_only_delete_their_own_documents(tmp_path):
    ingest_paths(ALICE, [write(tmp_path, "alice.md", ALICE_TEXT)], ["alice.md"])
    [doc] = list_documents(ALICE)
    assert doc["chunks"] == 1
    assert isinstance(doc["uploaded_at"], int)

    assert delete_document(BOB, doc["id"]) == 0
    assert list_documents(ALICE) == [doc]
    assert delete_document(ALICE, doc["id"]) == 1
    assert list_documents(ALICE) == []


@pytest.mark.parametrize("owner_id", ["", "../x", "A", "x" * 65, "a:b", "a-b", None])
def test_owner_ids_are_validated(owner_id):
    with pytest.raises(ValueError):
        collection_name(owner_id)


def test_documents_api_is_scoped_to_the_logged_in_user(make_client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 1024 * 1024)
    alice, bob = make_client("alice"), make_client("bob")

    response = alice.post(
        "/api/ingest", files={"files": ("alice.md", ALICE_TEXT.encode(), "text/markdown")}
    )
    assert response.status_code == 200
    assert response.json()["chunks_added"] == 1

    [doc] = alice.get("/api/documents").json()["documents"]
    assert doc["name"] == "alice.md"
    assert bob.get("/api/documents").json() == {"documents": [], "total_chunks": 0}

    # The agent's retrieval for each account sees only that account's uploads.
    alice_id = users.authenticate("alice", PASSWORD).id
    bob_id = users.authenticate("bob", PASSWORD).id
    assert ALICE_TEXT in search(alice_id)
    assert ALICE_TEXT not in search(bob_id)

    assert bob.delete(f"/api/documents/{doc['id']}").status_code == 404
    assert alice.get("/api/documents").json()["total_chunks"] == 1
    assert alice.delete(f"/api/documents/{doc['id']}").json() == {"deleted_chunks": 1}
    assert alice.get("/api/documents").json() == {"documents": [], "total_chunks": 0}
