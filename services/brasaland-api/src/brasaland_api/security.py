import os
import hashlib
import json
import logging
from pathlib import Path
import re
import secrets
import sqlite3
import time

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


logger = logging.getLogger(__name__)
APPROVAL_TTL_SECONDS = 300
_sensitive_paths = re.compile(
    r"^/(?:users/[^/]+|api/v1/(?:"
    r"reporting/pipeline/run|training/recipes/updates/publish|"
    r"training/onboarding/assign|hr/time-off/requests/[^/]+/action|"
    r"hr/onboarding/cases/(?:start|[^/]+/advance)|"
    r"customers/[^/]+/points/adjust|marketing/orders|inventory/receipts))/?$"
)


def required_secret(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value) < 32 or len(set(value)) < 12:
        raise RuntimeError(f"{name} must be explicitly configured with a strong secret")
    return value


def action_digest(method: str, target: str, payload: dict) -> str:
    encoded = json.dumps(
        {"method": method.upper(), "target": target, "payload": payload},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode()
    if len(encoded) > 65536:
        raise ValueError("Approval payload too large")
    return hashlib.sha256(encoded).hexdigest()


def approval_db() -> sqlite3.Connection:
    configured = os.environ.get("BRASALAND_APPROVAL_DB")
    if not configured:
        raise RuntimeError("BRASALAND_APPROVAL_DB must be configured")
    path = Path(configured)
    if not path.is_absolute():
        raise RuntimeError("BRASALAND_APPROVAL_DB must be an absolute path")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    path.chmod(0o600)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS security_approvals ("
        "token_hash TEXT PRIMARY KEY, actor_id TEXT NOT NULL, action_hash TEXT NOT NULL, "
        "expires_at REAL NOT NULL, used_at REAL)"
    )
    return connection


def issue_approval(actor_id: str, method: str, target: str, payload: dict) -> str:
    token = secrets.token_urlsafe(32)
    digest = action_digest(method, target, payload)
    connection = approval_db()
    try:
        with connection:
            connection.execute(
                "INSERT INTO security_approvals VALUES (?, ?, ?, ?, NULL)",
                (hashlib.sha256(token.encode()).hexdigest(), actor_id, digest,
                 time.time() + APPROVAL_TTL_SECONDS),
            )
    finally:
        connection.close()
    logger.info("security_approval action=approve actor_hash=%s action_hash=%s reason=explicit_admin_confirmation",
                hashlib.sha256(actor_id.encode()).hexdigest()[:16], digest)
    return token


def consume_approval(token: str | None, actor_id: str, method: str, target: str, payload: dict) -> None:
    if not token:
        raise PermissionError("Explicit human approval required")
    digest = action_digest(method, target, payload)
    connection = approval_db()
    try:
        with connection:
            cursor = connection.execute(
                "UPDATE security_approvals SET used_at = ? WHERE token_hash = ? "
                "AND actor_id = ? AND action_hash = ? AND expires_at > ? AND used_at IS NULL",
                (time.time(), hashlib.sha256(token.encode()).hexdigest(), actor_id, digest, time.time()),
            )
            if cursor.rowcount != 1:
                raise PermissionError("Approval invalid, expired or already used")
    finally:
        connection.close()
    logger.info("security_approval action=consume actor_hash=%s action_hash=%s reason=approved_exact_payload",
                hashlib.sha256(actor_id.encode()).hexdigest()[:16], digest)


class ConfirmationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, authenticate):
        super().__init__(app)
        self.authenticate = authenticate

    async def dispatch(self, request, call_next):
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"} or not _sensitive_paths.fullmatch(request.url.path):
            return await call_next(request)
        try:
            authorization = request.headers.get("Authorization", "")
            if not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="JWT required for sensitive actions")
            user = await self.authenticate(authorization[7:])
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Inactive account")
            raw = await request.body()
            if len(raw) > 65536:
                return JSONResponse({"detail": "Payload too large"}, status_code=413)
            payload = json.loads(raw) if raw else {}
            if not isinstance(payload, dict):
                raise ValueError("Invalid payload")
            target = request.url.path
            if request.url.query:
                target += "?" + request.url.query
            consume_approval(request.headers.get("X-Human-Approval"), user.id,
                             request.method, target, payload)
        except HTTPException as error:
            return JSONResponse({"detail": error.detail}, status_code=error.status_code)
        except (PermissionError, ValueError, RuntimeError, sqlite3.Error):
            logger.warning("security_approval action=reject reason=missing_or_invalid_confirmation")
            return JSONResponse({"detail": "Valid explicit human approval required"}, status_code=403)
        return await call_next(request)