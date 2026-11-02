import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.brasaland_api import auth, security
from src import main
from workflows.scripts import send_weekly_report


@pytest.fixture(autouse=True)
def isolated_approvals(tmp_path, monkeypatch):
    monkeypatch.setenv("BRASALAND_APPROVAL_DB", str(tmp_path / "approvals.sqlite3"))


def test_approval_is_bound_to_actor_and_payload_and_single_use():
    payload = {"points": 10}
    token = security.issue_approval("admin-id", "POST", "/sensitive", payload)
    with pytest.raises(PermissionError):
        security.consume_approval(token, "other-user", "POST", "/sensitive", payload)
    with pytest.raises(PermissionError):
        security.consume_approval(token, "admin-id", "POST", "/sensitive", {"points": 1000})
    security.consume_approval(token, "admin-id", "POST", "/sensitive", payload)
    with pytest.raises(PermissionError):
        security.consume_approval(token, "admin-id", "POST", "/sensitive", payload)


def test_expired_approval_fails(monkeypatch):
    token = security.issue_approval("admin-id", "DELETE", "/users/2", {})
    now = security.time.time()
    monkeypatch.setattr(security.time, "time", lambda: now + security.APPROVAL_TTL_SECONDS + 1)
    with pytest.raises(PermissionError):
        security.consume_approval(token, "admin-id", "DELETE", "/users/2", {})


def test_sensitive_endpoint_requires_explicit_approval():
    app = FastAPI()
    effects = []

    async def authenticate(_):
        return SimpleNamespace(id="admin-id", is_active=True)

    app.add_middleware(security.ConfirmationMiddleware, authenticate=authenticate)

    @app.post("/api/v1/marketing/orders")
    def create_order(payload: dict):
        effects.append(payload)
        return {"created": True}

    client = TestClient(app)
    payload = {"product": "test"}
    headers = {"Authorization": "Bearer simulated"}
    assert client.post("/api/v1/marketing/orders", json=payload, headers=headers).status_code == 403
    assert not effects
    token = security.issue_approval("admin-id", "POST", "/api/v1/marketing/orders", payload)
    headers["X-Human-Approval"] = token
    assert client.post("/api/v1/marketing/orders", json=payload, headers=headers).status_code == 200
    assert client.post("/api/v1/marketing/orders", json=payload, headers=headers).status_code == 403
    assert effects == [payload]


def test_only_active_admin_can_issue_approval():
    payload = auth.ApprovalRequest(method="DELETE", target="/users/2", payload={}, confirmed=True)
    with pytest.raises(auth.HTTPException) as error:
        auth.approve_action(payload, SimpleNamespace(id="user", role=auth.Role.user, is_active=True))
    assert error.value.status_code == 403


def test_real_delete_route_requires_admin_confirmation(isolated_user_store):
    admin = auth.create_user_in_db(auth.UserCreate(email="approver@example.com", password="synthetic-test-password"))
    victim = auth.create_user_in_db(auth.UserCreate(email="delete-test@example.com", password="synthetic-test-password"))
    auth.get_users_table().update({"role": auth.Role.admin.value}, doc_ids=[int(admin.id)])
    token = auth.create_access_token(admin.email, auth.Role.admin.value)
    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {token}"}
    target = f"/users/{victim.id}"
    assert client.delete(target, headers=headers).status_code == 403
    assert auth.get_user_by_email(victim.email) is not None
    approved = client.post("/auth/approvals", headers=headers, json={
        "method": "DELETE", "target": target, "payload": {}, "confirmed": True,
    })
    assert approved.status_code == 200
    headers["X-Human-Approval"] = approved.json()["approval_token"]
    assert client.delete(target, headers=headers).status_code == 204
    assert auth.get_user_by_email(victim.email) is None


def test_report_dispatch_requires_approval_for_exact_destinations(tmp_path, monkeypatch, capsys):
    report = tmp_path / "report.md"
    report.write_text("Synthetic report", encoding="utf-8")
    calls = []
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://slack.example.invalid/test")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("REPORT_APPROVAL_TOKEN", raising=False)
    monkeypatch.setattr(send_weekly_report, "send_to_slack", lambda *args: calls.append(args))
    monkeypatch.setattr(send_weekly_report.sys, "argv", ["send_weekly_report", "--report-path", str(report)])
    assert send_weekly_report.main() == 1
    assert not calls
    monkeypatch.setattr(send_weekly_report.sys, "argv", [
        "send_weekly_report", "--report-path", str(report), "--approval-manifest",
    ])
    assert send_weekly_report.main() == 0
    manifest = json.loads(capsys.readouterr().out)
    token = security.issue_approval("admin-id", "POST", "workflow:weekly-report", manifest)
    monkeypatch.setenv("REPORT_APPROVAL_TOKEN", token)
    monkeypatch.setenv("REPORT_APPROVER_ID", "admin-id")
    monkeypatch.setattr(send_weekly_report.sys, "argv", ["send_weekly_report", "--report-path", str(report)])
    assert send_weekly_report.main() == 0
    assert len(calls) == 1
    assert send_weekly_report.main() == 1
    assert len(calls) == 1