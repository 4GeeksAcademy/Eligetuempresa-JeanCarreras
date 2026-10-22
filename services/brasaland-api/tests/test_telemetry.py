import json
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient

from src.brasaland_api.analysis import (
    api_latency_by_day,
    availability_by_day_and_source,
    auth_failure_rate,
    error_rate_by_type,
    events_per_day,
)
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
    assert response.json() == {"received": 1}
    with main.get_db() as db:
        row = db.execute(
            "SELECT event_type, tags FROM telemetry_events"
        ).fetchone()
    assert row["event_type"] == "inventory_validation_failed"
    assert json.loads(row["tags"])["validation_code"] == "invalid_quantity"


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
    assert "not-allowed@example.com" not in response.text


def seed_operational_telemetry(db_path: Path) -> None:
    with connect(db_path) as db:
        db.execute(
            """
            CREATE TABLE telemetry_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                tags TEXT NOT NULL,
                request_id TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE store_telemetry_events (
                event_ts TEXT NOT NULL,
                source_system TEXT NOT NULL,
                latency_seconds REAL NOT NULL,
                pos_online INTEGER NOT NULL
            )
            """
        )
        db.executemany(
            """
            INSERT INTO store_telemetry_events (
                event_ts, source_system, latency_seconds, pos_online
            ) VALUES (?, ?, ?, ?)
            """,
            [
                ("2026-10-10T10:00:00+00:00", "pos", 2.0, 1),
                ("2026-10-10T12:00:00+00:00", "pos", 4.0, 0),
                ("2026-10-11T12:00:00+00:00", "network", 1.0, 1),
                ("2026-10-12T00:00:00+00:00", "pos", 9.0, 1),
            ],
        )
        db.executemany(
            """
            INSERT INTO telemetry_events (
                event_id, timestamp, event_type, tags, request_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    "api-ok-1",
                    "2026-10-10T10:00:00+00:00",
                    "api_latency_recorded",
                    json.dumps({"route_template": "/api/v1/orders", "status_code": 200, "duration_ms": 100, "request_count": 2}),
                    "request-1",
                ),
                (
                    "api-error-1",
                    "2026-10-10T12:00:00+00:00",
                    "api_latency_recorded",
                    json.dumps({"route_template": "/api/v1/orders", "status_code": 500, "duration_ms": 200, "request_count": 1}),
                    "request-2",
                ),
                ("auth-failed-1", "2026-10-10T13:00:00+00:00", "auth_login_failed", "{}", "request-3"),
                ("auth-failed-2", "2026-10-10T14:00:00+00:00", "auth_login_failed", "{}", "request-4"),
                ("auth-ok-1", "2026-10-10T15:00:00+00:00", "auth_login_succeeded", "{}", "request-5"),
                ("auth-ok-2", "2026-10-10T16:00:00+00:00", "auth_login_succeeded", "{}", "request-6"),
                (
                    "api-ok-2",
                    "2026-10-11T12:00:00+00:00",
                    "api_latency_recorded",
                    json.dumps({"route_template": "/api/v1/orders", "status_code": 200, "duration_ms": 60}),
                    "request-7",
                ),
                ("auth-ok-3", "2026-10-11T13:00:00+00:00", "auth_login_succeeded", "{}", "request-8"),
            ],
        )


def test_telemetry_analysis_returns_temporal_operational_metrics(tmp_path: Path) -> None:
    db_path = tmp_path / "telemetry.db"
    seed_operational_telemetry(db_path)
    start = datetime(2026, 10, 10, tzinfo=timezone.utc)
    end = datetime(2026, 10, 12, tzinfo=timezone.utc)

    assert events_per_day(start, end, db_path) == [
        {"date": "2026-10-10", "event_type": "api_latency_recorded", "event_count": 2},
        {"date": "2026-10-10", "event_type": "auth_login_failed", "event_count": 2},
        {"date": "2026-10-10", "event_type": "auth_login_succeeded", "event_count": 2},
        {"date": "2026-10-11", "event_type": "api_latency_recorded", "event_count": 1},
        {"date": "2026-10-11", "event_type": "auth_login_succeeded", "event_count": 1},
    ]
    assert api_latency_by_day(start, end, db_path)[0] == {
        "date": "2026-10-10",
        "route_template": "/api/v1/orders",
        "request_count": 3,
        "mean_latency_ms": 133.33,
    }
    assert error_rate_by_type(start, end, db_path)[0] == {
        "date": "2026-10-10",
        "event_type": "api_latency_recorded",
        "route_template": "/api/v1/orders",
        "request_count": 3,
        "error_count": 1,
        "error_rate_pct": 33.33,
    }
    assert auth_failure_rate(start, end, db_path) == [
        {
            "date": "2026-10-10",
            "failed_attempts": 2,
            "total_attempts": 4,
            "failure_rate_pct": 50.0,
        },
        {
            "date": "2026-10-11",
            "failed_attempts": 0,
            "total_attempts": 1,
            "failure_rate_pct": 0.0,
        },
    ]
    assert availability_by_day_and_source(start, end, db_path)[0] == {
        "date": "2026-10-10",
        "source_system": "pos",
        "event_count": 2,
        "online_count": 1,
        "availability_pct": 50.0,
    }


def test_telemetry_report_uses_utc_window_and_cache(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "telemetry.db"
    seed_operational_telemetry(db_path)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    main._telemetry_report_cache.clear()

    response = client.get(
        "/telemetry/report",
        params={
            "start_date": "2026-10-10T00:00:00Z",
            "end_date": "2026-10-12T00:00:00Z",
        },
    )

    assert response.status_code == 200
    report = response.json()
    assert report["period"] == {
        "from": "2026-10-10T00:00:00+00:00",
        "to": "2026-10-12T00:00:00+00:00",
    }
    assert report["metrics"]["events_per_day"][0]["event_count"] == 2

    def unexpected_recalculation(*_args, **_kwargs):
        raise AssertionError("cached report recalculated")

    monkeypatch.setattr(main, "events_per_day", unexpected_recalculation)
    cached_response = client.get(
        "/telemetry/report",
        params={
            "start_date": "2026-10-10T00:00:00Z",
            "end_date": "2026-10-12T00:00:00Z",
        },
    )
    assert cached_response.json() == report

    cache_key = (
        "2026-10-10T00:00:00+00:00",
        "2026-10-12T00:00:00+00:00",
    )
    main._telemetry_report_cache[cache_key] = (0.0, report)
    recalculations = 0

    def count_recalculation(*_args, **_kwargs):
        nonlocal recalculations
        recalculations += 1
        return report["metrics"]["events_per_day"]

    monkeypatch.setattr(main, "events_per_day", count_recalculation)
    expired_response = client.get(
        "/telemetry/report",
        params={
            "start_date": "2026-10-10T00:00:00Z",
            "end_date": "2026-10-12T00:00:00Z",
        },
    )
    assert expired_response.status_code == 200
    assert recalculations == 1
