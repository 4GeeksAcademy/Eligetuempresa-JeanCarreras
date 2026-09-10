from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from src import main


def test_session_token_recovers_its_user(registered_user) -> None:
    token = main.sign_auth_token(
        registered_user["id"], datetime.now(timezone.utc) + timedelta(minutes=5)
    )

    authenticated = main.get_authenticated_user(f"Bearer {token}")

    assert authenticated["id"] == registered_user["id"]


@pytest.mark.parametrize("authorization", [None, "", "Basic credentials"])
def test_session_requires_bearer_authentication(authorization) -> None:
    with pytest.raises(HTTPException) as error:
        main.get_authenticated_user(authorization)

    assert error.value.status_code == 401
    assert error.value.detail == "Missing bearer token"


def test_session_rejects_expired_token_at_boundary(registered_user) -> None:
    token = main.sign_auth_token(registered_user["id"], datetime.now(timezone.utc))

    with pytest.raises(HTTPException) as error:
        main.get_authenticated_user(f"Bearer {token}")

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid or expired bearer token"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-token",
        "payload.invalid-signature",
        "@@@.signature",
    ],
)
def test_session_rejects_malformed_or_tampered_token(token: str) -> None:
    with pytest.raises(HTTPException) as error:
        main.get_authenticated_user(f"Bearer {token}")

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid or expired bearer token"


def test_session_rejects_valid_token_for_deleted_user(registered_user) -> None:
    token = main.sign_auth_token(
        registered_user["id"], datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    with main.get_db() as db:
        db.execute("DELETE FROM users WHERE id = ?", (registered_user["id"],))

    with pytest.raises(HTTPException) as error:
        main.get_authenticated_user(f"Bearer {token}")

    assert error.value.status_code == 401
    assert error.value.detail == "User not found"