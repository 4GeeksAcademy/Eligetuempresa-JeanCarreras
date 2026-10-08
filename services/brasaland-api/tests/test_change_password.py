import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from src import main


def add_pending_reset(user_id: int) -> None:
    with main.get_db() as db:
        db.execute(
            "INSERT INTO password_reset_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (
                hashlib.sha256(b"pending-token").hexdigest(),
                user_id,
                (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            ),
        )


def test_change_password_updates_hash_and_invalidates_resets(
    registered_user,
) -> None:
    add_pending_reset(registered_user["id"])

    result = main.change_password(
        main.ChangePasswordRequest(
            current_password="secure-pass-123", new_password="new-pass-123"
        ),
        registered_user,
    )

    with main.get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE id = ?", (registered_user["id"],)
        ).fetchone()
        reset = db.execute("SELECT * FROM password_reset_tokens").fetchone()

    assert result == {"message": "Password updated successfully"}
    assert main.verify_password("new-pass-123", user["password_hash"])
    assert reset["used_at"] is not None


def test_change_password_accepts_minimum_length(registered_user) -> None:
    main.change_password(
        main.ChangePasswordRequest(
            current_password="secure-pass-123", new_password="12345678"
        ),
        registered_user,
    )

    with main.get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE id = ?", (registered_user["id"],)
        ).fetchone()

    assert main.verify_password("12345678", user["password_hash"])


def test_change_password_rejects_wrong_current_password(registered_user) -> None:
    with pytest.raises(HTTPException) as error:
        main.change_password(
            main.ChangePasswordRequest(
                current_password="wrong-password", new_password="new-pass-123"
            ),
            registered_user,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Current password is incorrect"


@pytest.mark.parametrize("new_password", ["", "short"])
def test_change_password_rejects_short_new_password(
    registered_user, new_password: str
) -> None:
    with pytest.raises(HTTPException) as error:
        main.change_password(
            main.ChangePasswordRequest(
                current_password="secure-pass-123", new_password=new_password
            ),
            registered_user,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Password must contain at least 8 characters"