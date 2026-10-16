from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from src import main
from src.brasaland_api import telemetry


client = TestClient(main.app)


@pytest.fixture
def supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://telemetry.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-server-key")
    request = httpx.Request("POST", "https://telemetry.example.test/rest/v1/telemetry_events")
    post = Mock(return_value=httpx.Response(201, json=[{"event_id": "stored"}], request=request))
    monkeypatch.setattr(telemetry.httpx, "post", post)
    return post


def telemetry_event(properties: dict[str, object]) -> dict[str, object]:
    return {
        "eventId": "fd8f7e48-93d3-4f1d-8a16-5961a40a2850",
        "timestamp": "2026-10-10T12:30:00Z",
        "sessionId": None,
        "userId": None,
        "event_type": "inventory_validation_failed",
        "schemaVersion": "1.0.0",
        "requestId": "b79d4c16-55f6-4e1c-9414-4c48a63fc478",
        "properties": properties,
    }


def test_telemetry_endpoint_accepts_a_valid_batch(supabase) -> None:
    response = client.post(
        "/telemetry/events",
        json={
            "events": [
                telemetry_event(
                    {
                        "country": "CO",
                        "validation_code": "invalid_quantity",
                        "operation": "receipt",
                    }
                )
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}
    supabase.assert_called_once()
    row = supabase.call_args.kwargs["json"][0]
    assert row["event_id"] == "fd8f7e48-93d3-4f1d-8a16-5961a40a2850"
    assert row["timestamp"] == "2026-10-10T12:30:00Z"
    assert row["event_type"] == "inventory_validation_failed"
    assert row["service"] == "brasaland-api"
    assert row["session_id"] is None
    assert row["user_id"] is None
    assert row["schema_version"] == "1.0.0"
    assert row["request_id"] == "b79d4c16-55f6-4e1c-9414-4c48a63fc478"
    assert row["tags"] == {"country": "CO", "validation_code": "invalid_quantity", "operation": "receipt"}


def test_telemetry_endpoint_rejects_properties_outside_the_allowlist(supabase) -> None:
    response = client.post(
        "/telemetry/events",
        json={
            "events": [
                telemetry_event(
                    {
                        "country": "CO",
                        "validation_code": "invalid_quantity",
                        "operation": "receipt",
                        "email": "not-allowed@example.com",
                    }
                )
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 0, "rejected": 1}
    assert "not-allowed@example.com" not in response.text
    supabase.assert_not_called()


def test_mixed_batch_is_validated_individually_and_inserted_once(supabase) -> None:
    valid = telemetry_event({"country": "CO", "store_id": "CO-01", "sku": "SKU-01", "validation_code": "invalid_quantity", "operation": "receipt"})
    technical = {**valid, "eventId": "fd8f7e48-93d3-4f1d-8a16-5961a40a2851", "event_type": "auth_login_failed", "properties": {"failure_code": "invalid_credentials", "auth_method": "password", "source_class": "web"}}
    invalid = {**valid, "properties": {**valid["properties"], "email": "private@example.com"}}
    supabase.return_value = httpx.Response(201, json=[{"event_id": valid["eventId"]}, {"event_id": technical["eventId"]}], request=supabase.return_value.request)

    response = client.post("/telemetry/events", json={"events": [valid, invalid, technical, None, "invalid", 42]})

    assert response.status_code == 200
    assert response.json() == {"received": 6, "stored": 2, "rejected": 4}
    supabase.assert_called_once()
    rows = supabase.call_args.kwargs["json"]
    assert len(rows) == 2
    assert rows[0]["tags"] == valid["properties"]
    assert rows[1]["tags"] == technical["properties"]
    assert "private@example.com" not in str(rows)


@pytest.mark.parametrize("payload", [{}, {"events": {}}, {"events": None}, [], {"events": "invalid"}])
def test_invalid_envelope_returns_422_without_inserting(payload, supabase) -> None:
    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 422
    supabase.assert_not_called()


def test_empty_batch_does_not_insert(supabase) -> None:
    response = client.post("/telemetry/events", json={"events": []})
    assert response.status_code == 200
    assert response.json() == {"received": 0, "stored": 0, "rejected": 0}
    supabase.assert_not_called()


def test_storage_failure_is_not_acknowledged(supabase) -> None:
    supabase.side_effect = httpx.ConnectError("secret upstream details")
    valid = telemetry_event({"country": "CO", "validation_code": "invalid_quantity", "operation": "receipt"})
    response = client.post("/telemetry/events", json={"events": [valid]})
    assert response.status_code == 503
    assert response.json() == {"detail": "Telemetry storage unavailable"}
    supabase.assert_called_once()


def test_missing_configuration_does_not_acknowledge_storage(supabase, monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY")
    valid = telemetry_event({"country": "CO", "validation_code": "invalid_quantity", "operation": "receipt"})
    response = client.post("/telemetry/events", json={"events": [valid]})
    assert response.status_code == 503
    supabase.assert_not_called()


def test_duplicates_are_counted_without_updating_existing_events(supabase) -> None:
    supabase.return_value = httpx.Response(201, json=[], request=supabase.return_value.request)
    valid = telemetry_event({"country": "CO", "validation_code": "invalid_quantity", "operation": "receipt"})
    response = client.post("/telemetry/events", json={"events": [valid]})
    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 0, "rejected": 1}
    supabase.assert_called_once()
    assert supabase.call_args.kwargs["params"]["on_conflict"] == "event_id"
    assert supabase.call_args.kwargs["headers"]["Prefer"] == "resolution=ignore-duplicates,return=representation"


@pytest.mark.parametrize("event_type,properties", [
    ("inventory_receipt_created", {
        "receipt_id": "receipt-test", "store_id": "CO-01", "country": "CO",
        "sku": "SKU-01", "received_qty": 10, "unit": "kg", "currency": "COP",
    }),
    ("inventory_outbound_order_submitted", {
        "order_id": "order-test", "store_id": "US-01", "country": "US",
        "sku": "SKU-01", "quantity": 2, "unit": "kg",
        "reason_code": "consumption", "movement_id": "movement-test",
    }),
    ("auth_login_failed", {
        "failure_code": "invalid_credentials", "auth_method": "password",
        "source_class": "web", "country": "CO",
    }),
])
def test_business_and_technical_dimensions_are_preserved(event_type, properties, supabase) -> None:
    event = {**telemetry_event(properties), "event_type": event_type}
    response = client.post("/telemetry/events", json={"events": [event]})
    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}
    supabase.assert_called_once()
    row = supabase.call_args.kwargs["json"][0]
    assert row["event_type"] == event_type
    assert row["tags"] == properties


@pytest.mark.parametrize("override", [
    {"eventId": "invalid"},
    {"timestamp": "2026-10-10T12:30:00"},
    {"event_type": "unknown_event"},
    {"schemaVersion": "2.0.0"},
    {"requestId": ""},
    {"properties": {}},
    {"properties": {"country": "XX", "validation_code": "invalid_quantity", "operation": "receipt"}},
    {"properties": {"country": True, "validation_code": "invalid_quantity", "operation": "receipt"}},
])
def test_invalid_contract_does_not_cancel_valid_siblings(override, supabase) -> None:
    valid = telemetry_event({"country": "CO", "validation_code": "invalid_quantity", "operation": "receipt"})
    response = client.post("/telemetry/events", json={"events": [valid, {**valid, **override}]})
    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 1, "rejected": 1}
    supabase.assert_called_once()
    assert len(supabase.call_args.kwargs["json"]) == 1


@pytest.mark.parametrize("status,payload", [
    (401, {"message": "private database details"}),
    (500, {"message": "private database details"}),
    (201, {"unexpected": "response"}),
])
def test_database_errors_return_a_safe_retryable_response(status, payload, supabase) -> None:
    supabase.return_value = httpx.Response(status, json=payload, request=supabase.return_value.request)
    valid = telemetry_event({"country": "CO", "validation_code": "invalid_quantity", "operation": "receipt"})
    response = client.post("/telemetry/events", json={"events": [valid]})
    assert response.status_code == 503
    assert response.json() == {"detail": "Telemetry storage unavailable"}