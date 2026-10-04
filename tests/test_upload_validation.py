import os
import tempfile


def track_temp_files(monkeypatch) -> list[str]:
    """Record every temp file the upload route creates."""
    created: list[str] = []
    real_mkstemp = tempfile.mkstemp

    def recording_mkstemp(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        created.append(path)
        return fd, path

    monkeypatch.setattr(tempfile, "mkstemp", recording_mkstemp)
    return created


def test_disallowed_extension_is_rejected(make_client):
    response = make_client().post(
        "/api/ingest", files={"files": ("script.exe", b"hello", "application/octet-stream")}
    )
    assert response.status_code == 415


def test_oversized_file_is_rejected(make_client):
    response = make_client().post(
        "/api/ingest", files={"files": ("note.txt", b"01234567890", "text/plain")}
    )
    assert response.status_code == 413


def test_empty_file_is_rejected(make_client):
    response = make_client().post(
        "/api/ingest", files={"files": ("note.txt", b"", "text/plain")}
    )
    assert response.status_code == 400


def test_unsafe_filename_is_not_used_as_path(make_client, monkeypatch):
    captured_paths: list[str] = []
    captured_names: list[str] = []

    def fake_ingest(owner: str, paths: list[str], names: list[str]) -> int:
        captured_paths.extend(paths)
        captured_names.extend(names)
        return 1

    monkeypatch.setattr("rag_agent.api.ingest_paths", fake_ingest)
    response = make_client().post(
        "/api/ingest",
        files={"files": ("../../outside.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200
    assert captured_paths
    assert all("outside.txt" not in path for path in captured_paths)
    assert captured_names == ["outside.txt"]
    assert response.json()["files"] == ["outside.txt"]


def test_temp_files_are_removed_when_a_later_file_fails_validation(make_client, monkeypatch):
    client = make_client()
    created = track_temp_files(monkeypatch)
    response = client.post(
        "/api/ingest",
        files=[
            ("files", ("ok.txt", b"hello", "text/plain")),
            ("files", ("bad.exe", b"hello", "application/octet-stream")),
        ],
    )
    assert response.status_code == 415
    assert len(created) == 1
    assert not os.path.exists(created[0])


def test_temp_files_are_removed_when_ingestion_fails(make_client, monkeypatch):
    client = make_client(raise_server_exceptions=False)
    created = track_temp_files(monkeypatch)

    def failing_ingest(owner: str, paths: list[str], names: list[str]) -> int:
        raise RuntimeError("embedding failed")

    monkeypatch.setattr("rag_agent.api.ingest_paths", failing_ingest)
    response = client.post(
        "/api/ingest", files={"files": ("note.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 500
    assert len(created) == 1
    assert not os.path.exists(created[0])
