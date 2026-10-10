from fastapi.testclient import TestClient

from src import main


client = TestClient(main.app)


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


def test_telemetry_endpoint_accepts_a_valid_batch() -> None:
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
    assert response.json() == {"received": 1}


def test_telemetry_endpoint_rejects_properties_outside_the_allowlist() -> None:
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

    assert response.status_code == 422
    assert "not-allowed@example.com" not in response.text