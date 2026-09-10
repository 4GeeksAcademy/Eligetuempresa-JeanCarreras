import pytest
from fastapi import HTTPException

from src import main


def test_login_returns_session_for_valid_credentials(registered_user) -> None:
    response = main.login(
        main.LoginRequest(email="owner@example.com", password="secure-pass-123")
    )

    authenticated = main.get_authenticated_user(f"Bearer {response.access_token}")

    assert response.token_type == "bearer"
    assert authenticated["id"] == registered_user["id"]


def test_login_normalizes_outer_spaces_and_email_case(registered_user) -> None:
    response = main.login(
        main.LoginRequest(email="  OWNER@EXAMPLE.COM  ", password="secure-pass-123")
    )

    authenticated = main.get_authenticated_user(f"Bearer {response.access_token}")

    assert authenticated["email"] == "owner@example.com"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("missing@example.com", "secure-pass-123"),
        ("owner@example.com", "wrong-password"),
        ("owner@example.com", ""),
    ],
)
def test_login_rejects_invalid_credentials(
    registered_user, email: str, password: str
) -> None:
    with pytest.raises(HTTPException) as error:
        main.login(main.LoginRequest(email=email, password=password))

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid email or password"