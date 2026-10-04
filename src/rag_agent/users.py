"""User accounts and login sessions, stored in a small SQLite database.

Passwords are hashed with scrypt from the standard library. A session is a random
token kept in an HttpOnly cookie. Only the token's SHA-256 hash is stored, so a
leaked database does not reveal usable tokens, and logging out deletes the session.

Create an account from the command line (needed when ALLOW_REGISTRATION=false):

    python -m rag_agent.users create <username>
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rag_agent.config import settings

SESSION_TTL_SECONDS = 60 * 60 * 24
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
USERNAME_RULES = (
    "Usernames must be 3-32 characters long and use only letters, numbers, dots, "
    "dashes or underscores, starting with a letter or number."
)
_USERNAME = re.compile(r"[a-z0-9][a-z0-9_.-]{2,31}")

# scrypt cost: N=2**14 and r=8 use 16 MiB per hash, within OpenSSL's default 32 MiB limit.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user_id ON sessions(user_id);
"""


@dataclass(frozen=True)
class User:
    # A random uuid4 hex string. It also names the user's private document collection,
    # so it must never be reused, even if the users database is recreated.
    id: str
    username: str


class UsernameTaken(Exception):
    def __init__(self) -> None:
        super().__init__("That username is already taken.")


# --- passwords ----------------------------------------------------------------


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = stored_hash.split("$")
        if algorithm != "scrypt":
            return False
        expected_digest = base64.b64decode(expected)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_digest),
        )
    except (ValueError, TypeError):  # malformed hash, or a password that is not valid UTF-8
        return False
    return hmac.compare_digest(digest, expected_digest)


@lru_cache
def _dummy_hash() -> str:
    """A real hash to check against when the username is unknown, so a failed login
    takes about as long whether or not the account exists."""
    return hash_password(secrets.token_urlsafe(16))


# --- validation -----------------------------------------------------------------


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_new_account(username: str, password: str) -> None:
    """Raise ValueError with a user-facing message if the account details are not allowed.

    ``username`` must already be normalized.
    """
    if not _USERNAME.fullmatch(username):
        raise ValueError(USERNAME_RULES)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Passwords must be at most {MAX_PASSWORD_LENGTH} characters long.")
    try:
        password.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("The password contains characters that are not allowed.") from None


# --- database -------------------------------------------------------------------

_initialized_paths: set[str] = set()
_init_lock = threading.Lock()


def init_db() -> None:
    """Create the database file and tables if needed. Safe to call repeatedly."""
    path = settings.users_db_path
    with _init_lock:
        if path in _initialized_paths:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=10)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
        finally:
            conn.close()
        _initialized_paths.add(path)


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    """A connection for one unit of work: committed on success, rolled back on error."""
    init_db()
    conn = sqlite3.connect(settings.users_db_path, timeout=10)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            yield conn
    finally:
        conn.close()


# --- accounts -------------------------------------------------------------------


def create_user(username: str, password: str) -> User:
    username = normalize_username(username)
    validate_new_account(username, password)
    user = User(id=uuid.uuid4().hex, username=username)
    password_hash = hash_password(password)
    try:
        with _db() as conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user.id, user.username, password_hash, int(time.time())),
            )
    except sqlite3.IntegrityError:
        raise UsernameTaken() from None
    return user


def authenticate(username: str, password: str) -> User | None:
    """Return the user if the username and password match, otherwise None."""
    username = normalize_username(username)
    with _db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        verify_password(password, _dummy_hash())
        return None
    if not verify_password(password, row[2]):
        return None
    return User(id=row[0], username=row[1])


# --- sessions -------------------------------------------------------------------


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: str) -> str:
    """Start a session for the user and return the token to put in the cookie."""
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with _db() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (_token_hash(token), user_id, now, now + SESSION_TTL_SECONDS),
        )
    return token


def user_for_session(token: str | None) -> User | None:
    """Return the user a valid, unexpired session token belongs to, otherwise None."""
    if not token or len(token) > 256:
        return None
    with _db() as conn:
        row = conn.execute(
            "SELECT users.id, users.username FROM sessions "
            "JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
            (_token_hash(token), int(time.time())),
        ).fetchone()
    return User(id=row[0], username=row[1]) if row else None


def delete_session(token: str | None) -> None:
    if not token or len(token) > 256:
        return
    with _db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


# --- command line -----------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m rag_agent.users", description="Manage user accounts."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Create an account (prompts for the password).")
    create.add_argument("username")
    args = parser.parse_args(argv)

    if args.command == "create":
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat password: "):
            parser.exit(1, "Passwords do not match.\n")
        try:
            user = create_user(args.username, password)
        except (ValueError, UsernameTaken) as exc:
            parser.exit(1, f"{exc}\n")
        print(f"Created user {user.username!r}.")


if __name__ == "__main__":
    main()
