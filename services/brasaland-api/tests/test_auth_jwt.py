import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.brasaland_api import auth


def create_user(email: str = "user@example.com") -> auth.UserInDB:
    return auth.create_user_in_db(
        auth.UserCreate(email=email, password="secure-pass-123", name="Test User")
    )


def assert_http_error(error, status_code: int, detail: str) -> None:
    assert error.value.status_code == status_code
    assert error.value.detail == detail


def test_access_token_round_trip(isolated_user_store) -> None:
    token = auth.create_access_token("user@example.com", auth.Role.user.value)

    payload = auth.decode_access_token(token)

    assert payload["sub"] == "user@example.com"
    assert payload["role"] == auth.Role.user.value
    assert payload["iss"] == "brasaland-api"


def test_decode_rejects_expired_token(isolated_user_store) -> None:
    token = auth.create_access_token(
        "user@example.com", auth.Role.user.value, timedelta(seconds=-1)
    )

    with pytest.raises(HTTPException) as error:
        auth.decode_access_token(token)

    assert error.value.status_code == 401
    assert str(error.value.detail).startswith("Token inválido o expirado:")


@pytest.mark.parametrize(
    ("payload", "expected_detail"),
    [
        (
            {"sub": "user@example.com", "iss": "brasaland-api"},
            "Token inválido: faltan claims",
        ),
        (
            {
                "sub": "user@example.com",
                "role": "unknown",
                "iss": "brasaland-api",
            },
            "Token inválido: rol desconocido 'unknown'",
        ),
    ],
)
def test_decode_rejects_invalid_claims(
    isolated_user_store, payload: dict, expected_detail: str
) -> None:
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = auth.jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)

    with pytest.raises(HTTPException) as error:
        auth.decode_access_token(token)

    assert_http_error(error, 401, expected_detail)


def test_current_user_resolves_valid_token(isolated_user_store) -> None:
    user = create_user()
    token = auth.create_access_token(user.email, user.role.value)

    current_user = asyncio.run(auth.get_current_user(token))

    assert current_user.id == user.id
    assert current_user.hashed_password != "***redacted***"


def test_current_user_rejects_deleted_account(isolated_user_store) -> None:
    token = auth.create_access_token("deleted@example.com", auth.Role.user.value)

    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.get_current_user(token))

    assert_http_error(error, 401, "Usuario no encontrado")


def test_login_returns_jwt_for_valid_credentials(isolated_user_store) -> None:
    create_user()

    response = auth.login(
        SimpleNamespace(username="user@example.com", password="secure-pass-123")
    )

    assert response.token_type == "bearer"
    assert response.expires_in == auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert auth.decode_access_token(response.access_token)["sub"] == "user@example.com"


def test_login_rejects_invalid_credentials(isolated_user_store) -> None:
    create_user()

    with pytest.raises(HTTPException) as error:
        auth.login(SimpleNamespace(username="user@example.com", password="wrong-pass"))

    assert_http_error(error, 401, "Email o contraseña inválidos")


def test_login_rejects_inactive_user(isolated_user_store) -> None:
    create_user()
    users = auth.get_users_table()
    users.update({"is_active": False}, doc_ids=[1])

    with pytest.raises(HTTPException) as error:
        auth.login(
            SimpleNamespace(username="user@example.com", password="secure-pass-123")
        )

    assert_http_error(error, 401, "Usuario inactivo")


def test_whoami_returns_public_identity_and_profile(isolated_user_store) -> None:
    user = create_user()

    result = asyncio.run(auth.whoami(user))

    assert result["email"] == user.email
    assert result["role"] == "user"
    assert result["profile"]["name"] == "Test User"


def test_role_validator_accepts_jwt_and_legacy_token(isolated_user_store) -> None:
    user = create_user()
    jwt_token = auth.create_access_token(user.email, user.role.value)
    validator = auth.require_roles({"user"})

    jwt_role = asyncio.run(validator(authorization=f"Bearer {jwt_token}"))
    legacy_role = asyncio.run(
        validator(
            authorization=None,
            x_api_role="user",
            x_api_token=auth.LEGACY_ROLE_TOKENS["user"],
        )
    )

    assert jwt_role == "user"
    assert legacy_role == "user"


@pytest.mark.parametrize(
    ("role", "token", "status_code"),
    [
        (None, None, 401),
        ("admin", "wrong-token", 401),
        ("admin", auth.LEGACY_ROLE_TOKENS["admin"], 403),
    ],
)
def test_role_validator_rejects_missing_invalid_or_forbidden_legacy_auth(
    isolated_user_store, role, token, status_code: int
) -> None:
    validator = auth.require_roles({"user"})

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            validator(authorization=None, x_api_role=role, x_api_token=token)
        )

    assert error.value.status_code == status_code