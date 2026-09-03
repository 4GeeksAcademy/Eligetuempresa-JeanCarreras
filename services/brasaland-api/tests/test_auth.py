import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import main


def make_client() -> TestClient:
    temporary_db = NamedTemporaryFile(suffix=".db", delete=False)
    temporary_db.close()
    main.DB_PATH = Path(temporary_db.name)
    main.init_db()
    return TestClient(main.app)


def add_reset_token(user_id: int, value: str, expires_at: datetime) -> None:
    with main.get_db() as db:
        db.execute(
            "INSERT INTO password_reset_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (hashlib.sha256(value.encode()).hexdigest(), user_id, expires_at.isoformat()),
        )


def test_password_reset_is_single_use_and_forgot_password_is_opaque():
    client = make_client()
    client.post("/auth/register", json={"email": "qa@example.com", "password": "old-pass-123"})
    with patch.object(main, "send_reset_email") as send_email:
        missing = client.post("/auth/forgot-password", json={"email": "missing@example.com"})
        existing = client.post("/auth/forgot-password", json={"email": "qa@example.com"})
    assert missing.status_code == 200
    assert existing.status_code == 200
    assert missing.json() == existing.json()
    send_email.assert_called_once()

    token = "single-use-token"
    add_reset_token(1, token, datetime.now(timezone.utc) + timedelta(minutes=30))
    first_reset = client.post("/auth/reset-password", json={"token": token, "new_password": "new-pass-123"})
    second_reset = client.post("/auth/reset-password", json={"token": token, "new_password": "another-pass"})
    assert first_reset.status_code == 200
    assert second_reset.status_code == 400


def test_expired_reset_token_is_rejected():
    client = make_client()
    client.post("/auth/register", json={"email": "expired@example.com", "password": "old-pass-123"})
    token = "expired-token"
    add_reset_token(1, token, datetime.now(timezone.utc) - timedelta(minutes=1))
    response = client.post("/auth/reset-password", json={"token": token, "new_password": "new-pass-123"})
    assert response.status_code == 400


def test_change_password_requires_current_password_and_bearer_session():
    client = make_client()
    register = client.post("/auth/register", json={"email": "change@example.com", "password": "old-pass-123"})
    access_token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    invalid = client.post("/auth/change-password", headers=headers, json={"current_password": "wrong-pass", "new_password": "new-pass-123"})
    valid = client.post("/auth/change-password", headers=headers, json={"current_password": "old-pass-123", "new_password": "new-pass-123"})
    assert invalid.status_code == 400
    assert valid.status_code == 200
