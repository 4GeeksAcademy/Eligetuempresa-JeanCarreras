"""Reproducible access-control evidence using disposable data and a stubbed RAG."""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "services/brasaland-api"))
    sys.path.insert(0, str(root))
    os.environ["BRASALAND_JWT_SECRET"] = secrets.token_hex(32)
    os.environ["BRASALAND_AUTH_SECRET"] = secrets.token_hex(32)
    os.environ["DO_NOT_TRACK"] = "1"
    for role in ("ADMIN", "EXECUTIVE", "OPERATIONS", "FINANCE", "MANAGER", "USER"):
        os.environ.pop(f"BRASALAND_{role}_TOKEN", None)
    for name in ("BRASALAND_BOOTSTRAP_ADMIN_EMAIL", "BRASALAND_BOOTSTRAP_ADMIN_PASSWORD"):
        os.environ.pop(name, None)

    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    from src.brasaland_api import auth, knowledge
    from src import main as api

    results = {}

    encoded = base64.urlsafe_b64encode(json.dumps({
        "sub": "1", "exp": int(datetime.now(timezone.utc).timestamp()) + 600,
    }).encode()).decode().rstrip("=")
    signature = hmac.new(b"brasaland-local-auth-secret", encoded.encode(), hashlib.sha256).hexdigest()
    try:
        api.get_authenticated_user(f"Bearer {encoded}.{signature}")
    except HTTPException as error:
        assert error.status_code == 401
        results["public_hmac_secret_forgery"] = error.status_code
    else:
        raise AssertionError("Token signed with public HMAC secret accepted")

    def rejected(call, expected_status):
        try:
            asyncio.run(call)
        except HTTPException as error:
            assert error.status_code == expected_status, error.status_code
            return error.status_code
        raise AssertionError("Unsafe access was accepted")

    results["public_admin_token"] = rejected(
        auth.require_roles({"admin"})(
            authorization=None, x_api_role="admin", x_api_token="brasaland-admin-token"
        ),
        401,
    )
    service_token = secrets.token_hex(32)
    os.environ["BRASALAND_OPERATIONS_TOKEN"] = service_token
    results["invalid_bearer_cannot_fallback"] = rejected(
        auth.require_roles({"operations"})(
            authorization="Bearer invalid", x_api_role="operations", x_api_token=service_token
        ),
        401,
    )
    results["provisioned_service_token"] = asyncio.run(
        auth.require_roles({"operations"})(
            authorization=None, x_api_role="operations", x_api_token=service_token
        )
    )
    calls = []
    knowledge.query = lambda question: calls.append(question) or "isolated-answer"
    app = FastAPI()
    app.include_router(knowledge.knowledge_router)
    client = TestClient(app)
    response = client.post("/knowledge/query", json={"question": "audit"})
    assert response.status_code == 401 and not calls
    results["anonymous_knowledge"] = response.status_code

    with tempfile.TemporaryDirectory() as temporary:
        auth.DB_PATH = str(Path(temporary) / "users.json")
        auth._db_instance = None
        auth.init_seed_users()
        assert not auth.get_all_users()
        results["default_accounts_created"] = 0
        user = auth.create_user_in_db(
            auth.UserCreate(email="audit@example.com", password=secrets.token_urlsafe(24))
        )
        token = auth.create_access_token(user.email, "user")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/knowledge/query", headers=headers, json={"question": "audit"})
        assert response.status_code == 403 and not calls
        results["forbidden_role"] = response.status_code
        auth.get_users_table().update({"role": "admin"}, doc_ids=[int(user.id)])
        response = client.post("/knowledge/query", headers=headers, json={"question": "audit"})
        assert response.status_code == 200 and len(calls) == 1
        results["authorized_admin"] = response.status_code
        api.build_realtime_digest = lambda: {"audit": 1}
        api_client = TestClient(api.app)
        with api_client.websocket_connect("/ws/realtime", subprotocols=["brasaland", token]) as socket:
            assert socket.accepted_subprotocol == "brasaland"
            assert socket.receive_json()["type"] == "snapshot"
        results["websocket_authorized_jwt"] = "snapshot"
        try:
            with api_client.websocket_connect("/ws/realtime?role=admin&token=brasaland-admin-token"):
                raise AssertionError("WebSocket URL token accepted")
        except WebSocketDisconnect as error:
            assert error.code == 4403
            results["websocket_url_token"] = error.code
        auth.get_users_table().update({"is_active": False}, doc_ids=[int(user.id)])
        response = client.post("/knowledge/query", headers=headers, json={"question": "audit"})
        assert response.status_code == 401 and len(calls) == 1
        results["inactive_account"] = response.status_code

        auth.get_users_table().insert({
            "email": "admin@brasaland.com",
            "hashed_password": auth.hash_password("brasaland-admin"),
            "is_active": True,
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        auth.init_seed_users()
        assert not auth.get_user_by_email("admin@brasaland.com").is_active
        results["existing_demo_admin"] = "disabled"
        auth.get_db().close()
        auth._db_instance = None

    for name, value in (
        ("BRASALAND_JWT_SECRET", "brasaland-jwt-secret-dev"),
        ("BRASALAND_AUTH_SECRET", "brasaland-local-auth-secret"),
        ("BRASALAND_JWT_SECRET", ""),
    ):
        os.environ[name] = value
        try:
            auth.require_secret(name)
        except RuntimeError:
            continue
        raise AssertionError("Known or missing signing secret accepted")
    results["known_and_missing_signing_secrets"] = "rejected"
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()