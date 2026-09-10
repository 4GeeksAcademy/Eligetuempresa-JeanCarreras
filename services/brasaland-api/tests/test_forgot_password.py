import hashlib
from datetime import datetime, timezone

from src import main


EXPECTED_MESSAGE = {
    "message": "Si esa dirección está registrada, recibirás un enlace en breve"
}


def test_forgot_password_stores_hashed_token_and_sends_link(
    registered_user, monkeypatch
) -> None:
    sent_messages = []
    monkeypatch.setattr(main.secrets, "token_urlsafe", lambda _: "plain-reset-token")
    monkeypatch.setattr(
        main, "send_reset_email", lambda email, url: sent_messages.append((email, url))
    )

    result = main.forgot_password(main.ForgotPasswordRequest(email="owner@example.com"))

    with main.get_db() as db:
        token = db.execute("SELECT * FROM password_reset_tokens").fetchone()

    assert result == EXPECTED_MESSAGE
    assert token["token_hash"] == hashlib.sha256(b"plain-reset-token").hexdigest()
    assert "plain-reset-token" not in token["token_hash"]
    assert datetime.fromisoformat(token["expires_at"]) > datetime.now(timezone.utc)
    assert sent_messages == [
        (
            "owner@example.com",
            f"{main.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token=plain-reset-token",
        )
    ]


def test_forgot_password_is_opaque_for_unknown_account(
    registered_user, monkeypatch
) -> None:
    sent_messages = []
    monkeypatch.setattr(
        main, "send_reset_email", lambda email, url: sent_messages.append((email, url))
    )

    known_message = main.forgot_password(
        main.ForgotPasswordRequest(email="missing@example.com")
    )

    with main.get_db() as db:
        token_count = db.execute(
            "SELECT COUNT(*) AS count FROM password_reset_tokens"
        ).fetchone()["count"]

    assert known_message == EXPECTED_MESSAGE
    assert token_count == 0
    assert sent_messages == []


def test_forgot_password_empty_email_does_not_create_or_send(
    monkeypatch,
) -> None:
    sent_messages = []
    monkeypatch.setattr(
        main, "send_reset_email", lambda email, url: sent_messages.append((email, url))
    )

    result = main.forgot_password(main.ForgotPasswordRequest(email="   "))

    with main.get_db() as db:
        token_count = db.execute(
            "SELECT COUNT(*) AS count FROM password_reset_tokens"
        ).fetchone()["count"]

    assert result == EXPECTED_MESSAGE
    assert token_count == 0
    assert sent_messages == []