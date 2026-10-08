import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from src import main


def add_reset_token(user_id: int, raw_token: str, expires_at: datetime) -> None:
    with main.get_db() as db:
        db.execute(
            "INSERT INTO password_reset_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (
                hashlib.sha256(raw_token.encode()).hexdigest(),
                user_id,
                expires_at.isoformat(),
            ),
        )


def test_reset_password_changes_hash_and_invalidates_pending_tokens(
    registered_user,
) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    add_reset_token(registered_user["id"], "used-token", expires_at)
    add_reset_token(registered_user["id"], "other-pending-token", expires_at)

    result = main.reset_password(
        main.ResetPasswordRequest(token="used-token", new_password="new-pass-123")
    )

    with main.get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE id = ?", (registered_user["id"],)
        ).fetchone()
        tokens = db.execute("SELECT * FROM password_reset_tokens").fetchall()

    assert result == {"message": "Password updated successfully"}
    assert main.verify_password("new-pass-123", user["password_hash"])
    assert not main.verify_password("secure-pass-123", user["password_hash"])
    assert all(token["used_at"] is not None for token in tokens)


def test_reset_token_is_single_use(registered_user) -> None:
    add_reset_token(
        registered_user["id"],
        "single-use-token",
        datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    payload = main.ResetPasswordRequest(
        token="single-use-token", new_password="new-pass-123"
    )

    main.reset_password(payload)

    with pytest.raises(HTTPException) as error:
        main.reset_password(payload)

    assert error.value.status_code == 400
    assert error.value.detail == "Invalid, expired, or already used reset token"


@pytest.mark.parametrize("raw_token", ["missing-token", "", "malformed.token"])
def test_reset_password_rejects_unknown_or_malformed_token(
    registered_user, raw_token: str
) -> None:
    with pytest.raises(HTTPException) as error:
        main.reset_password(
            main.ResetPasswordRequest(token=raw_token, new_password="new-pass-123")
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Invalid, expired, or already used reset token"


def test_reset_password_rejects_expired_token(registered_user) -> None:
    add_reset_token(
        registered_user["id"],
        "expired-token",
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    with pytest.raises(HTTPException) as error:
        main.reset_password(
            main.ResetPasswordRequest(
                token="expired-token", new_password="new-pass-123"
            )
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Invalid, expired, or already used reset token"


@pytest.mark.parametrize("new_password", ["", "short"])
def test_reset_password_rejects_short_password(
    registered_user, new_password: str
) -> None:
    add_reset_token(
        registered_user["id"],
        "valid-token",
        datetime.now(timezone.utc) + timedelta(minutes=30),
    )

    with pytest.raises(HTTPException) as error:
        main.reset_password(
            main.ResetPasswordRequest(
                token="valid-token", new_password=new_password
            )
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Password must contain at least 8 characters"