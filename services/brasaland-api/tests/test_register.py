import pytest
from fastapi import HTTPException

from src import main


def test_register_persists_user_and_returns_valid_session() -> None:
    response = main.register(
        main.RegisterRequest(email="new@example.com", password="secure-pass-123")
    )

    user = main.get_authenticated_user(f"Bearer {response.access_token}")

    assert user["email"] == "new@example.com"
    assert main.verify_password("secure-pass-123", user["password_hash"])
    assert user["password_hash"] != "secure-pass-123"


def test_register_normalizes_email_and_accepts_minimum_password() -> None:
    main.register(main.RegisterRequest(email="  EDGE@Example.COM ", password="12345678"))

    with main.get_db() as db:
        user = db.execute("SELECT * FROM users").fetchone()

    assert user["email"] == "edge@example.com"
    assert main.verify_password("12345678", user["password_hash"])


@pytest.mark.parametrize(
    ("email", "password", "expected_detail"),
    [
        ("", "secure-pass-123", "Valid email is required"),
        ("not-an-email", "secure-pass-123", "Valid email is required"),
        ("valid@example.com", "", "Password must contain at least 8 characters"),
        ("valid@example.com", "short", "Password must contain at least 8 characters"),
    ],
)
def test_register_rejects_invalid_fields(
    email: str, password: str, expected_detail: str
) -> None:
    with pytest.raises(HTTPException) as error:
        main.register(main.RegisterRequest(email=email, password=password))

    assert error.value.status_code == 400
    assert error.value.detail == expected_detail


def test_register_rejects_duplicate_email_case_insensitively() -> None:
    main.register(
        main.RegisterRequest(email="duplicate@example.com", password="secure-pass-123")
    )

    with pytest.raises(HTTPException) as error:
        main.register(
            main.RegisterRequest(
                email="DUPLICATE@example.com", password="another-pass-123"
            )
        )

    assert error.value.status_code == 409
    assert error.value.detail == "Email already registered"