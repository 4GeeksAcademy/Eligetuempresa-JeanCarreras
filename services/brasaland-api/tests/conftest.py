import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import main
from src.brasaland_api import auth


@pytest.fixture(autouse=True)
def isolated_auth_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "auth.db"
    monkeypatch.setattr(main, "DB_PATH", db_path)

    with main.get_db() as db:
        db.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                password_changed_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE password_reset_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )

    return db_path


@pytest.fixture
def registered_user():
    response = main.register(
        main.RegisterRequest(email="owner@example.com", password="secure-pass-123")
    )
    with main.get_db() as db:
        return db.execute(
            "SELECT * FROM users WHERE email = ?", ("owner@example.com",)
        ).fetchone()


@pytest.fixture
def isolated_user_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    if auth._db_instance is not None:
        auth._db_instance.close()
    monkeypatch.setattr(auth, "_db_instance", None)
    monkeypatch.setattr(auth, "DB_PATH", str(tmp_path / "users.json"))

    yield

    if auth._db_instance is not None:
        auth._db_instance.close()
        auth._db_instance = None