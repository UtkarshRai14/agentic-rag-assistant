import pytest

from rag_agent import users

PASSWORD = "correct-horse-battery"


def test_password_hash_round_trip():
    stored = users.hash_password(PASSWORD)
    assert stored.startswith("scrypt$")
    assert PASSWORD not in stored
    assert users.verify_password(PASSWORD, stored)
    assert not users.verify_password("wrong-password", stored)


def test_password_hashes_are_salted():
    assert users.hash_password(PASSWORD) != users.hash_password(PASSWORD)


@pytest.mark.parametrize("stored", ["", "plain", "md5$a$b$c$d$e", "scrypt$x$8$1$AAAA$AAAA"])
def test_malformed_hashes_never_verify(stored):
    assert not users.verify_password(PASSWORD, stored)


def test_usernames_are_normalized_and_unique():
    user = users.create_user("  Alice ", PASSWORD)
    assert user.username == "alice"
    assert len(user.id) == 32
    with pytest.raises(users.UsernameTaken):
        users.create_user("ALICE", "another-password")


def test_user_ids_are_unique():
    assert users.create_user("alice", PASSWORD).id != users.create_user("bob", PASSWORD).id


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("ab", PASSWORD),  # too short
        ("a" * 33, PASSWORD),  # too long
        ("has space", PASSWORD),
        ("-dash", PASSWORD),  # must start with a letter or digit
        ("bob", "short"),
        ("bob", "x" * (users.MAX_PASSWORD_LENGTH + 1)),
        ("bob", "\ud800" * 8),  # not encodable as UTF-8
    ],
)
def test_invalid_accounts_are_rejected(username, password):
    with pytest.raises(ValueError):
        users.create_user(username, password)


def test_authenticate():
    created = users.create_user("alice", PASSWORD)
    assert users.authenticate("Alice", PASSWORD) == created
    assert users.authenticate("alice", "wrong-password") is None
    assert users.authenticate("nobody", PASSWORD) is None


def test_sessions_can_be_looked_up_and_revoked():
    user = users.create_user("alice", PASSWORD)
    token = users.create_session(user.id)
    assert users.user_for_session(token) == user
    assert users.user_for_session(token + "x") is None
    assert users.user_for_session(None) is None
    users.delete_session(token)
    assert users.user_for_session(token) is None


def test_session_tokens_are_not_stored_in_plain_text():
    user = users.create_user("alice", PASSWORD)
    token = users.create_session(user.id)
    with users._db() as conn:
        stored = [row[0] for row in conn.execute("SELECT token_hash FROM sessions")]
    assert stored == [users._token_hash(token)]
    assert token not in stored


def test_sessions_expire(monkeypatch):
    user = users.create_user("alice", PASSWORD)
    token = users.create_session(user.id)
    real_time = users.time.time
    monkeypatch.setattr(users.time, "time", lambda: real_time() + users.SESSION_TTL_SECONDS + 1)
    assert users.user_for_session(token) is None
