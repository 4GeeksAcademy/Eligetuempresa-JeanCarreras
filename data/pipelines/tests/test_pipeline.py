import sqlite3
from datetime import datetime, timezone

from data.pipelines.pipeline import (
    extract_telemetry_events,
    load_reporting_rows,
    transform_telemetry_events,
)


def create_source_database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE stores (id TEXT PRIMARY KEY, name TEXT, country TEXT);
            CREATE TABLE store_telemetry_events (
                id INTEGER PRIMARY KEY,
                store_id TEXT,
                event_ts TEXT,
                ingested_at TEXT,
                latency_seconds REAL,
                pos_online INTEGER,
                sales_last_5m INTEGER,
                open_tickets INTEGER,
                avg_prep_seconds REAL,
                network_rtt_ms REAL
            );
            INSERT INTO stores VALUES ('med-001', 'Medellin', 'CO');
            INSERT INTO store_telemetry_events VALUES
                (1, 'med-001', '2026-10-12T10:00:00+00:00', '2026-10-12T10:00:01+00:00', 1, 1, 2, 3, 120, 15),
                (2, 'med-001', '2026-10-12T10:05:00+00:00', '2026-10-12T10:05:01+00:00', 1, 0, 4, 1, 180, 25);
            """
        )


def test_extract_reads_telemetry_without_writing(tmp_path):
    source_path = tmp_path / "source.db"
    create_source_database(source_path)

    events = extract_telemetry_events.fn(str(source_path))

    assert len(events) == 2
    with sqlite3.connect(source_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM store_telemetry_events").fetchone()[0] == 2


def test_transform_aggregates_daily_store_kpis(tmp_path):
    source_path = tmp_path / "source.db"
    create_source_database(source_path)
    events = extract_telemetry_events.fn(str(source_path))

    rows = transform_telemetry_events.fn(events)

    assert rows == [
        {
            "store_id": "med-001",
            "store_name": "Medellin",
            "country": "CO",
            "metric_date": "2026-10-12",
            "telemetry_events": 2,
            "pos_online_pct": 50.0,
            "avg_sales_last_5m": 3.0,
            "avg_open_tickets": 2.0,
            "avg_prep_seconds": 150.0,
            "avg_network_rtt_ms": 20.0,
            "avg_latency_seconds": 1.0,
        }
    ]


def test_load_is_idempotent_and_records_run_metadata(tmp_path):
    reporting_path = tmp_path / "reporting.db"
    rows = [
        {
            "store_id": "med-001",
            "store_name": "Medellin",
            "country": "CO",
            "metric_date": "2026-10-12",
            "telemetry_events": 1,
            "pos_online_pct": 100.0,
            "avg_sales_last_5m": 2.0,
            "avg_open_tickets": 1.0,
            "avg_prep_seconds": 100.0,
            "avg_network_rtt_ms": 10.0,
            "avg_latency_seconds": 1.0,
        }
    ]
    started_at = datetime.now(timezone.utc).isoformat()

    first_result = load_reporting_rows.fn(
        rows,
        run_id="run-1",
        started_at=started_at,
        records_processed=1,
        reporting_db_path=str(reporting_path),
    )
    second_result = load_reporting_rows.fn(
        rows,
        run_id="run-2",
        started_at=started_at,
        records_processed=1,
        reporting_db_path=str(reporting_path),
    )

    assert first_result["status"] == second_result["status"] == "completed"
    with sqlite3.connect(reporting_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM telemetry_daily_kpis").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0] == 2